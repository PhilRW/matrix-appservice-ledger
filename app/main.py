import logging
import os
import subprocess

import flask
import yaml
from matrix_client.api import MatrixHttpApi

CONFIG_DIR = os.environ.get("MATRIX_APPSERVICE_LEDGER_CONFIG_DIR", "../config/")
CONFIG_FILE = os.environ.get("MATRIX_APPSERVICE_LEDGER_CONFIG_FILE", "ledger-registration.yaml")
CONFIG_PATH = os.path.join(CONFIG_DIR, CONFIG_FILE)

logging.basicConfig(
    format='%(asctime)s | %(levelname)-8s | %(threadName)-22s | %(message)s',
    level=logging.DEBUG
)

logger = logging.getLogger(__name__)

if None in [CONFIG_DIR, CONFIG_FILE]:
    raise ValueError("Missing environment variable. Cannot continue.")

with open(CONFIG_PATH, 'r') as stream:
    try:
        config = yaml.safe_load(stream)
        AS_TOKEN = config["as_token"]
        HS_TOKEN = config["hs_token"]
        HS_URL = config["hs_url"]
        logger.debug(f"Loaded config: {config}")
    except KeyError as ke:
        raise ValueError(f"Cannot find key {ke} in configuration file.")
    except yaml.YAMLError as ye:
        raise

app = flask.Flask(__name__)
matrix = MatrixHttpApi(HS_URL, token=AS_TOKEN)


@app.route("/transactions/<txn_id>", methods=["PUT"])
def on_receive_events(txn_id):
    events = flask.request.get_json()["events"]
    for event in events:
        logger.info(f"User: {event['user_id']} Room: {event['room_id']}")
        logger.info(f"Event Type: {event['type']}")
        logger.info(f"Content: {event['content']}")
        logger.info(f"Room has {len(matrix.get_room_members(event['room_id']))} members in it.")
    return flask.jsonify({})


def shell(command) -> bytes:
    cmd = [
        "/bin/sh",
        "-c",
        command
    ]
    try:
        out = subprocess.check_output(cmd)
        logger.debug(out)
        return out
    except subprocess.CalledProcessError as cpe:
        logger.error(cpe)


if __name__ == "__main__":
    app.run("0.0.0.0")
