# Review: Payment Retry: Reference

Verdict: request changes. As written, every successful charge is sent again and again forever, and the first PSP incident after deploy would exhaust every checkout thread. The goal is right (survive transient PSP failures); the mechanism needs three things it lacks: idempotency, bounds and timeouts. A strong review explains the double-charge path concretely, proposes one retry policy (what is retried, how often, for how long, in which layer), and recognizes that the old `send` handled errors and interruption correctly and should be kept as the inner call.

A policy to propose:

```text
attempts: at most 3, and an overall deadline of ~10 s (inside the 30 s load-balancer budget, leaving room for the rest of checkout)
timeouts: connect 2 s, per request 4 s
retry only: connection failures, request timeouts, 429 (honoring Retry-After), 502, 503, 504
never retry: 400, 401, 402 and other 4xx; decode or programming errors
POSTs carry Idempotency-Key = "charge:" + paymentId (or the refund id), identical on every attempt and every checkout retry
backoff: exponential with full jitter (for example random(0, 200 ms x 2^attempt)), plus a circuit breaker
one retry layer: either PspClient or CheckoutService, not both
```

## Blocker

- `PspClient.java:67` `sendWithRetry`: success is `statusCode() == 200`, but the PSP answers `201 Created` for every new charge and refund. Every successful charge is treated as a failure and sent again after 1 s, 2 s, 3 s and so on, forever, and each attempt charges the card again (there is no idempotency key). The unit test passes only because the mock returns 200. Treat any 2xx as success (or the exact documented codes per endpoint) and test with the real status codes.
- `PspClient.java:32` `charge` and `:36` `refund`: retrying a POST without an idempotency key double-charges or double-refunds whenever the outcome is ambiguous: a timeout, a connection reset or a 5xx after the PSP has processed the request. Send `Idempotency-Key` derived from the business operation (`charge:{paymentId}`), not generated per attempt, so retries here and checkout retries from the mobile app collapse into one charge. Retrying `getCharge` (a GET) is safe as is.
- `PspClient.java:63` `while (true)`: retries every outcome forever, including permanent ones (402 declined, 400, 401). A declined card or a bad API key never returns to the shopper, and during a PSP incident (the case this PR is for) every request thread ends up sleeping in this loop: 200 threads per instance are exhausted within seconds and all of checkout goes down, not just card payments. The load balancer gives up after 30 s while the thread keeps charging, and the app retries, adding more threads. Bound attempts and total time, and retry only retryable failures.

## Major

- `PspClient.java:21` and `:44-56` no timeouts: the client has no `connectTimeout` and requests have no `.timeout(...)`, so a PSP that accepts connections and then stalls (last month's failure mode) blocks inside `httpClient.send` indefinitely; the retry logic never even runs. Add a connect timeout on the builder, a per-request timeout, and an overall deadline. A request that timed out has an unknown outcome, which is exactly why the idempotency key is mandatory before retrying it.
- `PspClient.java:71-72` `catch (Exception e)`: swallows the cause (the exception is not passed to the logger, so there is no stack trace) and retries everything, including programming errors and `json.decode` failures. If decoding a successful charge response fails, the charge succeeded and is sent again. Catch only I/O and timeout exceptions; let everything else propagate.
- `PspClient.java:76` interruption: `catch (InterruptedException ignored) {}`, and `catch (Exception e)` around `send`, both clear the interrupt flag and continue. Shutdown and request cancellation can never stop the loop, so a deploy waits for threads that will never finish. The previous code restored the flag (`Thread.currentThread().interrupt()`) and threw; keep that behavior.
- Error contract (`charge`, `refund`, `getCharge`): they still declare `throws PspException` but can no longer throw it. `CheckoutService`'s decline handling (showing the decline reason) is now dead code, and `PspException.fromResponse` with the decline code is no longer used. Map final outcomes to typed results or exceptions: declined (permanent, with the PSP's code) versus unavailable (transient, retryable by a higher layer).
- Retry amplification: `CheckoutService` already retries `PspException` 3 times. With retries in both layers the attempts multiply, and against a struggling PSP that turns a brownout into an outage. Decide on one layer; with an idempotency key the client layer is the natural place.

## Minor

- `PspClient.java:75` backoff: linear sleeps without jitter make every thread on every instance retry in lockstep after a blip, hitting the PSP in waves as it recovers. Use exponential backoff with full jitter, honor `Retry-After` on 429, and add a circuit breaker so an outage fails fast instead of holding threads.
- `PspClient.java:70-72` logging: no payment id, endpoint or response body, and one warning per attempt forever. Log the endpoint, payment id, status and attempt; log the final failure once at error level.
- `PspClientTest`: mocks 200 instead of the PSP's 201, sleeps for real (3 seconds for this test alone), and covers only the happy path. Add tests for 201 success, 402 not retried, 503 retried then failing after the attempt limit, the same `Idempotency-Key` header on every attempt, timeouts, and interruption stopping the loop. Inject the sleeper or the backoff policy so the tests run instantly.
- `PspClient.java:21` HTTP/2: an unrelated behavior change inside a retry fix. Split it out, confirm the PSP supports it (the JDK client falls back to HTTP/1.1 otherwise) and roll it out separately so a regression is attributable.

## Nit

- `PspClient.java:60` Javadoc: "retrying until the PSP answers successfully" accurately describes the infinite loop; once bounded, document the policy instead.
- `PspClient.java:62-63`: `for (int attempt = 1; attempt <= maxAttempts; attempt++)` reads better than a counter plus `while (true)`; better still, use a resilience library already on the classpath (for example Resilience4j or Failsafe) instead of hand-rolling retry, backoff and circuit breaking.
- `PspClient.java:75`: `1000L` is a magic number; make delays part of a configurable retry policy.
- `PspClient.java:47`, `:55`: `User-Agent` is duplicated in two builders; extract a shared request builder and include the service version.
