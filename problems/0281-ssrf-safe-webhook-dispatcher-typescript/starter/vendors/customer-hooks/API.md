# The customer server

A customer's webhook server on the internet, at `203.0.113.10`. Most names in this problem lead here. It takes your deliveries and answers as a real customer's server might, which is not always well.

## `POST /events` and `POST /v2/events`

Each answers 200 with `{"received": true}` to any delivery. Any other path answers 404.

## Scenarios

These are what you can try for yourself. They are not all it can do.

| Name | What it does |
|------|--------------|
| `outage` | Every request answers 500 |
| `slow` | Every request answers as usual, after 1.5 s |
| `gone` | Every request answers 410 |
| `flaky` | The first two requests answer 503, and every one after answers as usual |
| `huge_response` | `POST /events` answers 200 with a JSON body of 65,537 bytes |
| `redirect_to_metadata` | `POST /events` answers 302 with `Location: http://169.254.169.254/metadata/credentials` |
