# docker-compose:

1. `cp config/ledger-registration.sample.yaml config/ledger-registration.yaml`
2. edit `config/ledger-registration.yaml`

Add this to your matrix services `docker-compose.yaml`:

```yaml
  appservice-ledger:
    image: philrw/matrix-appservice-ledger
    build:
      context: ./matrix-appservice-ledger
    restart: unless-stopped
    volumes:
      - ./matrix-appservice-ledger/config:/data
      - /mnt/data/ledger:/ledger:ro
    environment:
      - "MATRIX_APPSERVICE_LEDGER_USERS=@somebody:your-homeserver.com"
      - "LEDGER_FILE=/ledger/finances.ledger"
      - "LEDGER_PRICE_DB=/ledger/price-db.ledger"
```