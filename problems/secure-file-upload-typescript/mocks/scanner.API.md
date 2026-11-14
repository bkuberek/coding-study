# The malware scanner

A vendor that scans files for malware. Your app sends it each upload and waits for its verdict. Like any vendor, it is sometimes slow, sometimes down, and sometimes asks you to slow down.

## `POST /v1/scan`

The body is the file's bytes, as they are. Send these headers:

| Header | Value |
|--------|-------|
| `Authorization` | `Bearer <SCANNER_API_KEY>` |
| `Content-Type` | `application/octet-stream` |
| `X-Content-Sha256` | The SHA-256 of the body, as 64 lowercase hex digits |

It answers 200 with a verdict:

```json
{"verdict": "clean"}
```

```json
{"verdict": "infected", "threat": "Test.File.Sample"}
```

A 429 means you sent too much too soon, and its `Retry-After` says how many seconds to wait. A 5xx means the vendor failed, and may not fail the next time.

## `GET /v1/status`

The vendor's status page: 200 with `{"status": "ok"}`. Your app does not need it.

## Scenarios

These are what you can try for yourself. They are not all it can do.

| Name | What it does |
|------|--------------|
| `infected` | Every scan answers 200 with `{"verdict": "infected", "threat": "Test.File.Sample"}` |
| `outage` | Every scan answers 503 |
| `slow` | Every scan answers as usual, after 1.5 s |
| `rate_limited_then_clean` | The first scan answers 429 with `Retry-After: 1`, and every one after answers clean |
