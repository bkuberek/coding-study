# Debug: Shared Default Config

## Statement

A multi-tenant API keeps settings per tenant. A tenant that has never been configured uses the defaults, and a change to one tenant must never reach another tenant or the defaults.

The defaults are 3 retries, 60 requests per minute, a limit of 10 on the route `/search` and no limit on other routes, and the notification channel `email`.

`TenantSettings` starts each tenant from a copy of the defaults. The reviewer of this code saw the spread and approved it. Find the bug and fix it.

### Bug report

> **Title:** Raising one tenant's limit raises it for everyone
>
> We raised `blue`'s rate limit to 500 and added `sms` as a channel. Tenant `green`, which nobody has configured, now also has 500 and `sms`, and so does every tenant created after that. Setting `retries` doesn't leak: each tenant keeps its own. A restart puts everything back to normal, until the next change. The bug is hard to reproduce in tests, which pass or fail depending on the order they run in.

## Input

- `new TenantSettings()`: no tenants configured yet.
- `tenant`, `route`, `channel`: names, as text.
- `setRetries(tenant, retries)`, `setRequestsPerMinute(tenant, requestsPerMinute)`, `setRouteLimit(tenant, route, limit)`, `addChannel(tenant, channel)`: change one tenant's settings.
- `reset(tenant)`: forgets the tenant's changes, so it uses the defaults again.
- `retries(tenant)`, `requestsPerMinute(tenant)`, `routeLimit(tenant, route)`, `channels(tenant)`: read one tenant's settings.

## Output

The setters and `reset` return nothing. The readers return the tenant's value, or the default for a tenant with no changes. `routeLimit` returns `-1` for a route with no limit, and `channels` returns the channels in the order they were added, the default one first.

## Examples

### Example 1

<!-- case: ex1 -->

`retries` is a number directly on the settings object, so a shallow copy is enough for it. This case passes as shipped.

### Example 2

<!-- case: ex2 -->

A tenant nobody has changed reads the defaults. This case can pass as shipped, as long as nothing has changed them yet.

## Constraints

- At most 1000 calls per test.
- Names are 1 to 20 printable ASCII characters.
- `0 <= retries, requestsPerMinute, limit <= 10^6`
- A channel is added at most once per tenant.

## Follow-ups

- A test passes alone and fails when the whole file runs. How would you recognize that this kind of shared state is the cause?
- `Object.freeze(DEFAULT_SETTINGS)` looks like it stops this. Does it? What would you need instead, and would you want it in production code?

## Hints

### Hint 1

Log `settings.limits === DEFAULT_SETTINGS.limits` after the copy.

### Hint 2

Why does `retries` work, while `limits` doesn't? What does `{ ...obj }` copy, for a value that is a number, and for one that is an object?

### Hint 3

How deep does the settings object go? Check every level of it, not just the first.

### Hint 4

`structuredClone` makes a deep copy, and so does a function that builds a new defaults object on each call.
