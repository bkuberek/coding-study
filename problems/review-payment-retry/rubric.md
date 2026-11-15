# Review: Payment Retry: Rubric

## Finding the issues

- [ ] Notices that only 200 counts as success while the PSP answers 201, so successful charges are repeated.
- [ ] Flags retried POSTs without an idempotency key as a double-charge risk on ambiguous failures.
- [ ] Flags the unbounded loop and connects it to thread-pool exhaustion and a full checkout outage.
- [ ] Flags that permanent failures (declines, 400, 401) are retried.
- [ ] Flags the missing connect and request timeouts, and that a stalled call never reaches the retry logic.
- [ ] Flags `catch (Exception)` swallowing the cause and retrying decode or programming errors.
- [ ] Flags the swallowed interrupt and notes the old code handled it correctly.
- [ ] Notices that `PspException` can no longer be thrown, breaking decline handling in the caller.
- [ ] Flags retry amplification with the existing retries in `CheckoutService`.
- [ ] Flags linear backoff without jitter and the test that mocks the wrong status code and sleeps for real.

## Prioritization

- [ ] Leads with the money-losing and outage-causing issues, before logging and style.
- [ ] Distinguishes what the change introduced from what it made worse (timeouts were already missing, but retries make them critical).
- [ ] Gives an overall verdict with a short reason.

## Actionable comments

- [ ] Proposes a concrete retry policy: attempt limit, deadline, retryable conditions, backoff with jitter, `Retry-After`.
- [ ] Derives the idempotency key from the payment, the same across attempts and checkout retries.
- [ ] Suggests keeping the old `send` as the inner call and wrapping it, or using an existing resilience library.
- [ ] Lists the missing tests (201, 402, retry limit, idempotency header, timeout, interruption) and asks for injectable delays.

## Tone and collaboration

- [ ] Acknowledges the incident action item and the intent of the change.
- [ ] Explains failures as scenarios (what the shopper and the PSP see), not as rule violations.
- [ ] Suggests splitting the unrelated HTTP/2 change without making it a blocker.

## Asking about intent

- [ ] Asks for the checkout latency budget to size the deadline.
- [ ] Asks which layer should own retries.
- [ ] Asks whether refunds should be retried synchronously or queued for asynchronous retry.
