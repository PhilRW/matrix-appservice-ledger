FROM python:3

ENV MATRIX_APPSERVICE_LEDGER_CONFIG_DIR "/data"
ENV MATRIX_APPSERVICE_LEDGER_CONFIG_FILE "ledger-registration.yaml"

COPY install/requirements.txt .
RUN pip install -r requirements.txt

WORKDIR /app
COPY app/ .

VOLUME [ "/data" ]

ENTRYPOINT [ "python", "main.py" ]