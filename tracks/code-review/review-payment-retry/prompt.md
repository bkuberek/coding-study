# Review: Payment Retry

## Context

The checkout service (Java 21, Spring Boot) charges shoppers' cards through a payment service provider (PSP). `PspClient` wraps the PSP's REST API. Last month the PSP had a 20-minute partial outage (slow responses, timeouts and some 503s) and checkout failed for many shoppers; one action item from the incident review was "add retries to the PSP client". This pull request implements it.

Facts about the codebase and the PSP that are not visible in the diff:

- `POST /v1/charges` and `POST /v1/refunds` answer `201 Created` when they create a charge or refund, `402` for a declined card (with a decline code), `400` for an invalid request, `401` for a bad API key, `429` with `Retry-After` when rate limited, and occasionally `5xx`.
- The PSP supports an `Idempotency-Key` header: a repeated key within 24 hours replays the original response instead of creating a second charge.
- `ChargeRequest` carries `paymentId`, the id of the payment row the checkout service creates before charging.
- `CheckoutService.placeOrder` catches `PspException`: declines are shown to the shopper with the decline reason; other failures are retried up to 3 times.
- Requests run on a Tomcat pool of 200 threads per instance. The load balancer times out after 30 seconds, and the mobile apps retry a checkout that timed out.

## Pull request

**Retry PSP calls on failure**

> Incident follow-up: transient PSP failures should not fail checkout, so every PSP call now retries with linear backoff until it succeeds. Also switches the HTTP client to HTTP/2. Added a unit test that fails twice and then succeeds.

## Task

Review the change as you would a teammate's pull request, in about 40 minutes. For each issue, give its location, its severity (blocker, major, minor or nit), what goes wrong (in production terms: money, threads, shoppers) and the change you would ask for. Ask about intent where the right fix depends on it. End with your overall verdict.
