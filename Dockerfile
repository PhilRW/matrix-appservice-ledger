FROM ubuntu

ENV DEBIAN_FRONTEND "noninteractive"
ENV MATRIX_APPSERVICE_LEDGER_CONFIG_DIR "/data"
ENV MATRIX_APPSERVICE_LEDGER_CONFIG_FILE "ledger-registration.yaml"

WORKDIR /usr/src
RUN apt-get update
RUN apt-get install -y build-essential cmake doxygen libboost-system-dev libboost-dev python-dev gettext git libboost-date-time-dev libboost-filesystem-dev libboost-iostreams-dev libboost-python-dev libboost-regex-dev libboost-test-dev libedit-dev libgmp3-dev libmpfr-dev texinfo tzdata
RUN git clone git://github.com/ledger/ledger.git

WORKDIR /usr/src/ledger
RUN ./acprep update
RUN make check
RUN make install

WORKDIR /app
RUN apt-get install -y python3 python3-pip
COPY install/requirements.txt .
RUN pip3 install -r requirements.txt
COPY app/ .

VOLUME [ "/data", "/ledger" ]

ENTRYPOINT [ "waitress-serve", "main:app" ]