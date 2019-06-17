import argparse
import logging
import os
import signal
import subprocess
import threading
import time

from matrix_client.client import MatrixClient
from matrix_client.errors import MatrixError
from matrix_client.room import Room

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
SH_TIMEOUT = int(os.environ.get("SH_TIMEOUT", "8"))

logger = logging.getLogger(__name__)

logging.basicConfig(
    format='%(asctime)s | %(levelname)-8s | %(threadName)-22s | %(message)s',
    level=LOG_LEVEL
)


class MatrixBotLedger(threading.Thread):

    def __init__(
            self,
            homeserver: str,
            username: str,
            password: str,
            allowed_users: str,
            kill_event: threading.Event):
        super().__init__()
        logger.debug("__init__()")

        self.allowed_users = allowed_users.split(',')
        self.homeserver = homeserver
        self.kill_event = kill_event
        self.password = password
        self.sh_timeout = SH_TIMEOUT
        self.username = username

        self.client = MatrixClient(self.homeserver)
        self.allowed_users.append(self.username)
        logger.debug(f"allowed users: {self.allowed_users}")

    def run(self) -> None:
        logger.debug("run()")

        self.connect()

        for room_id in self.client.rooms:
            self.join_room(room_id)

        self.client.start_listener_thread(timeout_ms=5000, exception_handler=self.listener_exception_handler)
        self.client.add_invite_listener(self.on_invite)
        self.client.add_leave_listener(self.on_leave)

        self.kill_event.wait()
        logger.info("Logging out.")
        self.client.logout()

    def connect(self):
        try:
            self.client.login(username=self.username, password=self.password, limit=0)
            logger.info(f"connected to {self.homeserver}")
        except MatrixError as me:
            if not self.kill_event.is_set():
                logger.warning(f"connection to {self.homeserver} failed, retrying in 5 seconds... ({me})")
                time.sleep(5)
                self.connect()

    def listener_exception_handler(self, e):
        self.connect()

    def on_invite(self, room_id, state):
        _sender = "someone"
        for _event in state["events"]:
            if _event["type"] != "m.room.join_rules":
                continue
            _sender = _event["sender"]
            break
        logger.info(f"invited to {room_id} by {_sender}")
        if _sender not in self.allowed_users:
            logger.info(f"no whitelist match, ignoring invite from {_sender}")
            return
        self.join_room(room_id)

    def join_room(self, room_id):
        logger.info(f"join_room({room_id})")

        room = self.client.join_room(room_id)
        room.add_listener(self.on_room_event)

    # TODO: debug this
    def on_leave(self, room_id, state):
        logger.debug(f"on_leave({room_id}, {state})")

        sender = "someone"
        for event in state["timeline"]["events"]:
            if not event["membership"]:
                continue
            sender = event["sender"]
        logger.info(f"kicked from {room_id} by {sender}")

    def on_room_event(self, room: Room, event):
        logger.debug(f"on_room_event({room}, {event}")

        if event["sender"] == self.client.user_id:
            return
        if event["type"] != "m.room.message":
            return
        if event["content"]["msgtype"] != "m.text":
            return
        content_body = event["content"]["body"]
        body, html = None, None
        if content_body.startswith('!echo '):
            message = content_body[6:]
            logger.info(f"Echoing message '{message}' to room {room}")
            body = message
        elif content_body.startswith('!sh '):
            body, html = self.run_local_command('!sh ', content_body)
        elif content_body.startswith('!ledger '):
            body, html = self.run_local_command('!ledger ', content_body, keep_prefix=True)
        if body:
            self.safe_send_message(room, body, html)

    def run_local_command(self, prefix: str, command: str, keep_prefix: bool = False) -> tuple:
        command = command[len(prefix):]
        body, html = None, None
        if keep_prefix:
            command = prefix[1:] + command
        try:
            body = self.__sh(command)
            html = f"<pre>{body}</pre"
        except subprocess.CalledProcessError as cpe:
            logger.warning(cpe)
            body = f"command failed: {cpe}"
        except subprocess.TimeoutExpired as te:
            logger.warning(te)
            body = f"command timed out: {te}"

        return body, html

    def __sh(self, command) -> str:
        cmd = [
            "/bin/sh",
            "-c",
            command
        ]
        return subprocess.check_output(cmd, timeout=self.sh_timeout).decode()

    def safe_send_message(self, room: Room, body: str, html: str):
        members = room.get_joined_members()
        logger.debug(f"room joined members: {members}")
        for u in members:
            if u.user_id not in self.allowed_users:
                body = "I'm sorry, but not everyone in this room has clearance, so I'm not going to respond."
                html = None
                break
        try:
            room.send_html(html, body)
        except MatrixError as me:
            logger.error(me)


if __name__ == "__main__":

    kill_event = threading.Event()


    def on_signal(sgnl, frame):
        logger.debug(f"on_signal({sgnl}, {frame})")

        kill_event.set()


    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)

    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--homeserver",
                        help="https://matrix.example.com",
                        default=os.environ.get("HOMESERVER"))
    parser.add_argument("-u", "--username",
                        help="@ledger:matrix.example.com",
                        default=os.environ.get("USERNAME"))
    parser.add_argument("-p", "--password",
                        default=os.environ.get("PASSWORD"))
    parser.add_argument("-al", "--allowed_users",
                        help="@user1:matrix.example.com,@user2.matrix.example.com",
                        default=os.environ.get("ALLOWED_USERS"))

    args = parser.parse_args()
    if not args.homeserver \
            or not args.username \
            or not args.password \
            or not args.allowed_users:
        parser.print_usage()
        exit(1)

    mbl = MatrixBotLedger(args.homeserver,
                          args.username,
                          args.password,
                          args.allowed_users,
                          kill_event)
    mbl.start()

    try:
        while not kill_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Ctrl-C caught, attempting to close threads.")

        kill_event.set()
        mbl.join()

        logger.info("Quitting app.")
