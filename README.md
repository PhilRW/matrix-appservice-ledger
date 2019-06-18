# docker-compose:

Add this to your matrix services `docker-compose.yaml`:

```yaml
  appservice-ledger:
    image: philrw/matrix-bot-ledger
    restart: unless-stopped
    environment:
      - "HOMESERVER=https://matrix.example.com"
      - "USERNAME=@ledger:matrix.example.com"
      - "PASSWORD=12345"
      - "ALLOWED_USERS=@somebody:matrix.example.com,@somebody-else:matrix.example.com"
      - "LEDGER_FILE=/ledger/finances.ledger"
      - "LEDGER_PRICE_DB=/ledger/price-db.ledger"
    volumes:
      - /mnt/data/ledger:/ledger:ro  # wherever your LEGER_FILE and/or LEDGER_PRICE_DB are located
```