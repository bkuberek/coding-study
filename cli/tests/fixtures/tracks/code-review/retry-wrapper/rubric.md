# Retry Wrapper: Rubric

## Correctness

- [ ] Notices that retrying a charge without an idempotency key can charge twice.
- [ ] Notices that the last failure is swallowed and the function returns None.

## Style

- [ ] Asks for backoff with jitter instead of a fixed sleep.
