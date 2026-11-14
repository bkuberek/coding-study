# The partner server

Another customer's webhook server on the internet, at `198.51.100.20` and at `172.32.0.10`. `inbox.partner.test` leads here.

## `POST /inbox` and `POST /events`

Each answers 200 with `{"received": true}` to any delivery. Any other path answers 404.

## Scenarios

These are what you can try for yourself. They are not all it can do.

| Name | What it does |
|------|--------------|
| `outage` | Every request answers 500 |
