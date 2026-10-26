# Retry Wrapper: Reference

## Blocker

- `charge`: retrying a POST without an idempotency key can charge the customer twice.

## Major

- `with_retries`: after the last attempt the exception is swallowed and `None` is returned.
- `except Exception` also retries programming errors such as `TypeError`.

## Nit

- A fixed one-second sleep; prefer exponential backoff with jitter.
