# Distributed Rate Limiter

## Question

Design the rate limiting layer for a public API platform. A fleet of API gateway nodes receives every request; before forwarding a request to a backend, a gateway must decide whether the caller is within its limits. Limits protect backends from overload and enforce what each customer's plan pays for.

## Functional requirements

- Limits apply per API key, per user, per IP address or per organization, optionally scoped to an endpoint (for example `POST /v1/messages`).
- A caller can be subject to several rules at once, such as 100 requests per second with bursts of 200 and 1 million requests per day.
- Rejected requests get HTTP 429 with `Retry-After`; every response carries headers telling the caller its limit, what remains and when it resets.
- Operators change rules and per-customer overrides at runtime, without a deploy, and can trial a new rule in a log-only mode first.
- Some limits are global across regions (daily quotas); others are per region.

## Non-functional requirements

- The check sits in the request path: it may add at most 2 ms at p99.
- A limiter outage must not take the API down. Most rules fail open; a few protect expensive or abuse-prone endpoints (login, sending SMS) and must fail closed.
- Accuracy: under normal operation, admit no more than about 5% above a limit; never reject a caller who is clearly under it.
- Rule changes take effect within 30 seconds.

## Scale

- 50 million API keys, of which 2 million are active in any hour.
- 1 million requests per second at peak, across three regions; the largest region takes 40%.
- 300 gateway nodes.
- About 1,000 rule definitions plus 100,000 per-customer overrides.
- Traffic is skewed: the largest customers send 50,000 requests per second on a single key.
