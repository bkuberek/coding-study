# API Gateway: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| route-trie | optimal | O(L) per route registration; O(2^L) worst case and O(L) typical per request; amortized O(1) per limit check | O(R L + A) | default answer; each concern is its own small class behind the facade |

Here `L` is the number of segments in a pattern or path, `R` the number of routes, and `A` the number of accepted requests a sliding window remembers.

## How the design grows level by level

| Level | New requirement | What the design adds |
|-------|-----------------|----------------------|
| 1 | Register routes and pick the most specific match | `RouteTable`: one trie per method, with literal children, one shared parameter child and a wildcard slot per node |
| 2 | Fixed-window limit per client | `Client` with a `RateLimiter`; `FixedWindow` keeps the current window number and a count |
| 3 | Sliding windows and lifetime quotas | `SlidingWindow`, a second `RateLimiter`; a `quota` counter on `Client`, checked together with the limiter |
| 4 | Circuit breakers per upstream | `CircuitBreaker`, a three-state machine whose state is computed from the time it opened |

`route` is a pipeline: match, then the breaker check, then the client check, then record. The rule that makes it correct is "check everything, then record": nothing is counted until every check has passed, so a request rejected at any step leaves no trace in a limiter, a quota or a breaker's trial slot. Adding level 4 inserts one check and one record step; nothing else moves.

## Approach: route-trie (Route trie with per-client limiters and per-upstream breakers)

### Intuition

The specificity rule, "at the first differing segment, a literal beats a parameter beats `*`", is a lexicographic order over the segments. A trie searched depth-first in that preference order visits candidate routes in exactly that order, so the first complete match it finds is the best one; no scoring is needed. Parameter names do not affect matching, so all parameters at one position share a single child, which also makes "same shape" duplicates collide naturally.

The policies are independent objects with tiny interfaces. A rate limiter answers `allows(now)` and takes `record(now)`, whichever window it uses. A breaker never needs a timer: it remembers when it opened and derives `OPEN` or `HALF_OPEN` from the current time.

### Algorithm

1. Route table: split a pattern into segments. Walk or create the trie of its method, taking the literal child for a literal and the shared parameter child for `:name`. A pattern ending in `*` stores its upstream in the `wildcard` slot of the node before the `*`; any other pattern stores it in the node's `upstream` slot. `addRoute` refuses an occupied slot, and `removeRoute` clears it.
2. Matching `path` at node `n` and position `i`: if `i` is the end of the path, return `n.upstream`. Otherwise try the literal child for segment `i`, then the parameter child, each at `i + 1`; if neither finds a route, return `n.wildcard`, which matches the one or more segments left.
3. `FixedWindow`: window number `t / windowMs`. It allows a request when the window changed since the last accepted one, or the count is below the limit. `record` resets the count when the window changed, then adds one.
4. `SlidingWindow`: a queue of accepted times. `allows(t)` drops the times at or before `t - windowMs`, then compares the queue length with the limit. `record` appends `t`.
5. `Client`: `allows` requires the limiter (if any) and `quota > 0` (if a quota is set). `record` records in the limiter and decrements the quota. Setting a limit or a quota replaces the object or the counter, which starts counting from zero.
6. `CircuitBreaker`: `state(t)` is `CLOSED` without an opening time, `HALF_OPEN` when `t >= openedAt + cooldown`, and `OPEN` otherwise. `allows` is true when closed, or when half-open with no trial in flight. A dispatch while half-open marks the trial in flight. A result while closed updates the consecutive-failure count and opens at the threshold; while half-open it closes on success or reopens at `t` on failure; while open it is ignored.
7. `route(t, client, method, path)`: match or return `"404"`; if the upstream's breaker does not allow, return `"503"`; if the client does not allow, return `"429"`; then record in the client and dispatch through the breaker, and return the upstream.

### Correctness

Matching: for two patterns that both match a path, the trie paths of the two patterns agree up to their first differing position, where one goes to a literal child, a parameter child or the wildcard slot. The search tries those in the preference order and only falls back when the preferred subtree contains no match at all, so it returns the first matching pattern in the lexicographic order of the rule. Distinct shapes that match the same path always differ somewhere, so the best route is unique.

Rate limits: a fixed window allows a request exactly when fewer than `limit` accepted requests share its window number, because the count is reset the first time a later window is recorded. A sliding window allows a request at `t` exactly when fewer than `limit` accepted times lie in `(t - windowMs, t]`: timestamps increase, so every time it drops is also outside every later window.

Breakers: the state only changes through `record` and the passage of time, and both transitions match the statement. At most one trial can be in flight while half-open, because a dispatch sets the flag and only a result clears it.

Nothing is recorded for rejected requests, because each check happens before any `record`. The order of checks (`404`, `503`, `429`) is the order of the pipeline.

### Complexity

- Time: O(L) per route registration; O(2^L) worst case and O(L) typical per request; amortized O(1) per limit check — registration walks one trie path. Matching can backtrack from a literal subtree into the parameter subtree at every level, which is exponential only for adversarial route sets where every level has both kinds and matches fail deep down; with ordinary APIs it is a single path. Each accepted time enters and leaves a sliding window once.
- Space: O(R L + A) — the trie stores each pattern's segments once, and a sliding window remembers up to `limit` accepted times.

### Trade-offs

- A list of routes scanned linearly with a specificity score per route is simpler and correct, at O(R L) per request. It is a fine first answer; the trie is the natural improvement when the interviewer asks about thousands of routes.
- A fixed window is one counter, but lets a client burst `2 * limit` requests across a window boundary. A sliding log, as here, is exact but stores up to `limit` timestamps per client. A sliding-window counter (weighted average of the current and previous fixed windows) or a token bucket gives a close approximation in O(1) memory; both fit the same `RateLimiter` interface.
- Deriving `HALF_OPEN` from the clock avoids timers and keeps the breaker deterministic and testable. Real breakers often count failures over a rolling window rather than consecutive failures; that is a change inside `CircuitBreaker` only.
- Limits are per gateway instance. Sharing them across instances needs an external store with atomic increments, which changes `record` into a remote call; that is the scale follow-up.

### Pitfalls and edge cases

- `*` matches one or more segments, never zero: `/files/*` does not match `/files`.
- `/users/:id` and `/users/:uid` are the same shape; the second registration fails, and removing either name removes the route.
- When the literal subtree contains no complete match, the search must fall back to the parameter subtree, then the wildcard; returning "not found" after the literal branch fails is the classic bug.
- Fixed windows are aligned to multiples of `windowMs`, not to the first request.
- A request exactly `windowMs` after an accepted one no longer counts in the sliding window.
- A half-open trial rejected by the client's limit must not use the trial slot; that is why the breaker's dispatch is recorded last.
- Results reported while the breaker is open are stale and must not close it.

### Language notes

- Python: small classes with `__init__`; a `deque` for the sliding window. Methods named after the statement (`set_client_limit`) follow the runner's snake_case mapping.
- TypeScript: `RateLimiter` is an `interface` with two classes implementing it, which is erasable type syntax. The sliding window keeps an array and a start index instead of `shift()`, which is O(n). Optional chaining with `??` (`literal?.match(...) ?? parameter?.match(...) ?? wildcard`) expresses the search order in one expression.
- Java: private nested classes and a private `interface RateLimiter`; the breaker's state is an `enum` with `name()` producing the strings. The quota is a nullable `Long` so that "no quota" is distinct from 0.
- Kotlin: the same structure with file-private classes, `when` over the `enum class` for the state machine, and `?:` chains in `match`. `quota?.minus(1)` decrements only when a quota is set.
- Go: the limiter is a small `limiter` interface that the fixed and sliding windows satisfy, and a nil interface means "no limit". An optional upstream is a `*string`, so `nil` is "no route here"; `slot` hands back the field (`**string`) a pattern stores into, which lets `add` and `remove` share one lookup. The sliding window drops expired starts by re-slicing the front (`accepted = accepted[1:]`).
- Rust: the trie owns its children directly (`HashMap<String, RouteNode>` and `Option<Box<RouteNode>>` for the parameter child), so no `Rc` is needed, and `end` returns a `&mut RouteNode` walked down with `node = node.child(part)`. The two limiters are variants of one `Limiter` enum, matched where Python calls a method on the union; the breaker state is a `Copy` enum with a `name()`.
