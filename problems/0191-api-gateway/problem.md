# API Gateway

## Statement

Build `ApiGateway`, the front door of a set of backend services. It receives requests from clients, picks the backend service (the upstream) that should handle each one, and protects both sides: clients get rate limits and quotas, and failing upstreams get circuit breakers. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

The gateway does not forward anything itself. `route` answers with the upstream's name, or with an HTTP-style status code as a string when the request is rejected. Every method takes the current time as its first argument, `timestamp`, in milliseconds; nothing reads a clock.

## Input

- `ApiGateway()`: creates a gateway with no routes.
- `timestamp`: the time of the call. Within one test, timestamps strictly increase from call to call.
- `method`: an HTTP method in capitals, such as `GET` or `POST`.
- `pattern`, `path`: either `/` or `/` followed by segments separated by `/`; segments are never empty.
- `upstream`: the name of a backend service; it starts with a lowercase letter.
- Each level's section describes the methods it adds and their other parameters.

## Output

Each method returns what its level describes. `route` returns an upstream name or a status code string, and other failures use `false`, `""` or `-1`; nothing throws.

## Level 1: Route matching

- `addRoute(timestamp, method, pattern, upstream)`: registers a route. A pattern segment is either a literal, which matches the same path segment exactly; a parameter `:name`, which matches any one segment; or `*`, allowed only as the last segment, which matches one or more remaining segments. Two patterns have the same shape when they differ only in parameter names. Returns `false` and changes nothing when a route with the same method and shape exists.
- `removeRoute(timestamp, method, pattern)`: removes the route with this method and shape. Returns `false` when there is none.
- `route(timestamp, clientId, method, path)`: the upstream of the best route for this method that matches `path`, or `"404"` when none matches. When several routes match, compare their patterns segment by segment from the left; at the first position where they differ, a literal beats a parameter, and a parameter beats `*`. `clientId` names the caller; this level does not use it.

### Example 1

<!-- case: ex1 -->

`/users/:uid` has the same shape as `/users/:id`, so it is rejected. `/users/me` matches both remaining user routes and the literal wins; `/users/42` only matches the parameter. `*` needs at least one segment, so `/files` matches nothing, and no route exists for `POST`.

## Level 2: Fixed-window client limits

- `setClientLimit(timestamp, clientId, limit, windowMs)`: the client may have at most `limit` accepted requests per window. Windows are fixed: window `k` covers times `k * windowMs` to `(k + 1) * windowMs - 1`.
- A request over the limit gets `"429"`. Only accepted requests count: a `"404"` or a rejected request uses up nothing.
- Setting a limit replaces the client's earlier limit and counts only requests accepted from then on. Clients without a limit are unlimited.

### Example 1

<!-- case: ex2 -->

`mobile` may make 2 requests per second. Its third request in the window from 0 to 999 gets `429`, even at 999; `web` has no limit. At 1000 a new window starts.

## Level 3: Sliding windows and quotas

- `setClientSlidingLimit(timestamp, clientId, limit, windowMs)`: like `setClientLimit`, but the window slides: a request at time `t` is accepted only if fewer than `limit` of the client's accepted requests happened at times `s` with `t - windowMs < s <= t`. A client has one rate limit at a time: setting a limit of either kind replaces the other kind too.
- `setClientQuota(timestamp, clientId, quota)`: from now on the client may have at most `quota` accepted requests in total; further requests get `"429"`. Replaces any earlier quota.
- `remainingQuota(timestamp, clientId)`: how many more requests the quota allows, or `-1` when the client has no quota.
- A request is accepted only when both the rate limit and the quota allow it; a rejected request uses up neither.

### Example 1

<!-- case: ex3 -->

`bot` may make 2 requests in any 100 ms. At 90 the requests at 10 and 50 are both within the window; at 110 the one at 10 has left it. With a quota of 1, the request at 300 uses it up and the one at 400 is rejected. `human` has no quota.

## Level 4: Circuit breakers

- `setBreaker(timestamp, upstream, failureThreshold, cooldownMs)`: installs a circuit breaker for `upstream`, replacing any earlier one. It starts `"CLOSED"`.
- `reportResult(timestamp, upstream, success)`: tells the breaker how a forwarded request ended, and returns its state afterwards, or `""` when the upstream has no breaker.
  - `"CLOSED"`: a success resets the count of consecutive failures; a failure adds one, and when the count reaches `failureThreshold` the breaker becomes `"OPEN"`.
  - `"OPEN"`: results are ignored. Once `cooldownMs` has passed since it opened, the breaker is `"HALF_OPEN"`.
  - `"HALF_OPEN"`: a success closes it with no failures counted; a failure opens it again, and the cooldown restarts from this report.
- `breakerState(timestamp, upstream)`: the breaker's state at `timestamp`, or `""` when the upstream has no breaker.
- In `route`, after matching: an `"OPEN"` upstream gets `"503"`. A `"HALF_OPEN"` upstream lets exactly one trial request through; until a result is reported, other requests get `"503"`. The checks run in this order: `"404"`, then `"503"`, then `"429"`; a request rejected at any step uses up nothing, not even the trial.

### Example 1

<!-- case: ex4 -->

Two consecutive failures open the breaker at 20, so the request at 30 gets `503`. The cooldown of 1000 ends at 1020, when the breaker becomes half-open. The request at 1021 is the trial; the one at 1022 is rejected while the trial is pending. A successful report closes the breaker again.

## Constraints

- At most 1000 calls per test.
- `1 <= timestamp <= 10^9`, strictly increasing within a test.
- Patterns and paths have at most 8 segments; segments are 1 to 10 characters from letters, digits, `.`, `-` and `_` (pattern segments may also be `:name` or `*`).
- `1 <= limit <= 1000`, `1 <= windowMs <= 10^9`, `0 <= quota <= 10^6`.
- `1 <= failureThreshold <= 100` and `1 <= cooldownMs <= 10^9`.
- Client ids are 1 to 10 lowercase letters or digits.

## Follow-ups

- How would you share rate-limit state between several gateway instances?
- Which other policies (retry budgets, weighted upstreams) would fit into the same request pipeline?

## Hints

### Hint 1

Store patterns in a trie per method: one child per literal and a single shared child for every parameter. Searching literal first, then parameter, then `*` finds the best route first.

### Hint 2

Give each client one limiter object behind a common interface (`allows(t)`, `record(t)`), so a fixed window and a sliding window are interchangeable. A fixed window only needs its window number and a count; a sliding window needs the times of its accepted requests.

### Hint 3

A breaker's state is a function of the time: store when it opened, and compute `"HALF_OPEN"` from the cooldown instead of waiting for an event. Check everything before recording anything, so a rejected request leaves no trace.
