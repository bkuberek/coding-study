# Price Cache and Rate Limits (TypeScript): Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | per request | per cached price and per client | default answer: every limit is decided by one script in the store, every missing price is fetched once, and a hot price that expires is served stale while one request refreshes it |

## How the project grows level by level

| Level | New requirement | What the code adds |
|-------|-----------------|--------------------|
| 1 | Keep prices for as long as the engine says, and say where each answer came from | `lifetimeOf` in `src/cacheControl.ts`, and `lookUp` with `fetchAndKeep` in `src/prices.ts` |
| 2 | At most 5 requests a second per API key, under bursts | `SLIDING_WINDOW` and `waitBeforeNext` in `src/limiter.ts`, and `limited` in `src/server.ts`, in front of every route but `/health` |
| 3 | Writes that drop the kept price, and one engine call per missing price | `putPrice` in `src/pricing.ts`, `setPrice` and `forget`, and `fetchOnce`, the single flight in `src/prices.ts` |
| 4 | Hot prices served stale while one request refreshes them | `staleS` in the lifetime, `freshUntil` beside the body, and the stale branch of `lookUp`, which starts `fetchOnce` without awaiting it |

## Approach: reference (One atomic script per limit, one fetch per missing price, and stale prices served while one request refreshes them)

### Intuition

A cache and a rate limiter look like two features, and they share one lesson: the store is the only place that sees every request, so anything that must hold across requests is decided there, in one step, or not at all.

The cache is cache-aside: look in the store, and on a miss ask the engine and write what it said, with the expiry it gave. The store forgets the key by itself, so no code has to remember to clean up, and a price can never outlive what the engine allowed. Errors are not prices, so they are never written.

The limiter is where the shared lesson bites. The obvious code reads the client's count, compares it with 5, and writes it back plus one. Twenty requests that arrive together all read the same count before any of them writes, and all twenty go through. The fix is not a faster read: it is making the read, the decision and the write one operation. The store runs a Lua script whole, with no other command in between, so a script that trims the client's window, counts it, and adds the request only when there is room cannot be raced. A sorted set per client, with each let-through request scored by its time, is the sliding window: the members older than a second are the ones that no longer count.

The stampede is the cache's version of the same race, inside your own process. Ten requests miss the desk at once, and each asks the engine: ten slow calls for one answer. Single flight keeps the promise of the fetch in progress per SKU, so the first request starts it and the other nine await the same promise. Writing the price into the store is part of that promise, so a request that arrives a moment later finds it kept.

Hot keys add the last idea. Even with single flight, every request for an expired hot price waits for the slow engine. If the engine allows a price to be shown for a while after it expires, the old price is good enough to answer at once while one background fetch replaces it. The key keeps its body for `max-age` plus `stale-while-revalidate`, beside the moment it stops being fresh, so a read can tell hit from stale with no second key.

### Say it out loud

"Cache-aside: on a request I look the price up in the store. If it's there it's a hit. If not, I ask the engine, and if it answered 200 I store its body with `SET ... EX` for the `max-age` it gave, or 30 seconds, and nothing at all for `no-store` or `max-age=0`. Failures are never stored.

"The limit is a sliding window per API key in a sorted set, and the check is one Lua script: drop entries older than a second, count, and add this request only if there are fewer than five, then set an expiry so idle clients disappear. The store runs the script alone, so a burst of twenty is counted one by one and exactly five pass. When it refuses, the script tells me when the oldest entry leaves the window, which is `Retry-After`. A get-then-set version passes every test that sends one request at a time and fails the moment requests arrive together.

"Writes go to the engine first and delete the key only once it accepted them, and the next read fetches whatever the engine now says. Concurrent misses share one in-flight promise per SKU, so the engine sees one call however many clients miss together, and they all get the same answer, error included.

"For hot prices I store the body with a TTL of fresh plus stale time and the moment it stops being fresh. Before that it's a hit; after, I answer the old body as stale and start the same single-flight fetch in the background, so one refresh runs however many requests see it stale."

### Algorithm

1. Every `/prices` request: check `X-Api-Key` against `^[A-Za-z0-9_-]{1,64}$`, else 401. Run the sliding-window script on `limit:<key>`; a non-zero answer is 429 with `Retry-After` its milliseconds rounded up to seconds.
2. `GET`: read `price:<sku>`. Missing: single flight. Present and before `freshUntil`: 200, `hit`. Present and after it: 200, `stale`, and start the single flight without awaiting it.
3. Single flight: if a fetch for the SKU is running, await it. Otherwise ask the engine. A 200 with a lifetime is stored as `{body, freshUntil}` with `EX` fresh plus stale seconds, and answered as a `miss`; a 404 is `unknown_sku`; anything else, or no answer within 5 s, is `pricing_unavailable`. The entry leaves the map when the fetch settles.
4. `PUT`: check `amount_cents`, else 400. Send it to the engine; anything but 204 is 502. Then `DEL price:<sku>` and answer 204.

### Design

| File | Holds |
|------|-------|
| `src/cacheControl.ts` | `lifetimeOf`: the fresh and stale seconds a `Cache-Control` header allows, or none |
| `src/limiter.ts` | `SLIDING_WINDOW`, the Lua script, and `waitBeforeNext`, which runs it for one client |
| `src/prices.ts` | `lookUp`, `forget`, and the single flight `fetchOnce` with `fetchAndKeep` |
| `src/pricing.ts` | The engine's client: `fetchPrice` and `putPrice` |
| `src/store.ts` | The store's client, unchanged from the starter |
| `src/server.ts` | The routes, `limited` in front of them, and the checks on a write's body |

The script uses the store's own clock, `TIME`, rather than the app's, so any number of copies of the app agree on what a second is. Each member of the set is a fresh UUID, because two requests in the same millisecond would otherwise be one member and count once.

`lookUp` returns a small result type rather than an HTTP answer, so the cache knows nothing about status codes and the route maps each outcome to one.

### Correctness

The store executes a script atomically, so for one client the scripts of a burst run one after another: each sees the set the previous one left, and the fifth `ZADD` is the last to happen while `ZCARD` is below 5. A refused request adds nothing, so it takes nothing from the allowance. Members older than the window are removed before counting, so a client that waited a second counts zero again. The key's expiry is refreshed with each request let through and is the window's length, so it outlives every member it holds and an idle client's key goes away.

A price is stored only from a 200 that allows it, with an expiry of exactly the time the engine gave plus any stale time, so the store forgets it by itself and no read can see it after that. Within the fresh time a read answers from the store and never calls the engine; after it, until the key expires, a read answers stale and the engine sees at most one fetch at a time for that SKU. JavaScript runs one callback at a time, so checking the map and putting the promise in it happen with no request in between: of the requests that miss together, exactly one starts the fetch. The map entry goes when the fetch settles, success or failure, so a failure is never served from the map to a later request.

A write deletes the key only after the engine answered 204, so a refused write leaves the kept price as it was, and an accepted one guarantees that the next read starts a fetch.

### Complexity

- Time: per request — one script with a few sorted-set operations on at most 5 members, one `GET`, and on a miss one engine call shared by every request that missed together
- Space: per cached price and per client — one key per kept price, and one sorted set of at most 5 members per client active in the last second

### Trade-offs

A fixed window, `INCR` on a key per client and second with an expiry, is atomic too, and simpler. It lets a client send 5 at the end of one second and 5 at the start of the next, 10 in a few milliseconds, which is why the statement asks for a sliding window or a token bucket. A token bucket stores two numbers per client instead of a set, and smooths a client's rate rather than capping each second; it needs the same single script, since it reads, refills and spends in one step.

Single flight in a `Map` holds for one process. Three copies of the service would each send one call, three in all, which is usually fine; when it is not, the lock moves into the store: `SET lock:<sku> <id> NX PX <ms>`, with the losers waiting for the price to appear. That brings its own questions, such as what happens when the holder dies, which is why the reference keeps the simpler version the statement allows.

There is a race the cases do not reach: a `GET` misses and waits for the engine, a `PUT` lands and deletes the key, and then the `GET` stores the old price, which stays for its whole `max-age`. Deleting the key again a moment after the write, or storing a version with each price and refusing to overwrite a newer one, closes it.

The reference does not handle the store going down. The `error` listener in `src/store.ts` keeps a lost connection from ending the process, but the client queues commands until it reconnects, so a request waits rather than failing. A real deployment chooses per use: the cache should fail open, treating an error as a miss so prices still come from the engine, and the limiter fails open or closed by what it protects. Either way the client needs a short command timeout and its offline queue turned off, so a dead store answers in milliseconds instead of hanging every request. The sandbox cannot stop the store in the middle of a case, so no case grades it.

Serving stale prices is a business decision as much as a technical one. A promotion that ends and keeps showing its price for 30 seconds may be fine for a lamp and not for a flight; `stale-while-revalidate` is the engine's way of saying which prices can bear it.

### Pitfalls and edge cases

**Wrong approaches.** Each fails a case, and the failure names what it did. Parallel cases send their burst at once, behind a barrier, and repeat from an empty store, so a race that loses only now and then still fails. None of these are stored as solutions: a pass of a parallel case finds no race and proves none, and the broken solutions are checked by hand until the grader's D7 runs them. The first three rows were run on a real stack, with the messages shown; the others name the cases written to catch them.

| What it does | Why it is wrong | What catches it |
|--------------|-----------------|-----------------|
| Counts with `GET`, compares in the app, then `SET` | Every request of a burst reads the same count before any writes, so all of them go through, while every case that sends one request at a time passes | `v6`, `h20`, `h22`, `h24` on their first run: `20 requests at once: expected 5 to answer 200 and 15 to answer 429; 20 answered 200` |
| Misses go straight to the engine, with no single flight | Ten requests that miss together make ten slow calls, and a stale hot price starts a refresh per request | `v8`, `h30`, `h36` to `h39`, `v10`, `h54`: `pricing desk: expected 1 request, saw 10`, and for the stale clock `pricing clock: expected 2 requests, saw 11` |
| Asks the engine every time, as the starter does | Nothing is kept | Every level 1 case but `h1` and `h7`: `header X-Cache: expected "hit", and it is missing; pricing chair: expected 1 request, saw 2` |
| `SET` with no expiry, or with a fixed one that ignores `max-age` | A price outlives what the engine allowed | `v3`, and `h2`, `h3` for one that keeps what it should not |
| `INCR` with no expiry, or a sorted set that is never trimmed | A client that spent its five never gets them back | `h25` |
| Stores 5xx answers, or a 404, as if they were prices | A failure is served after the engine recovered | `h6` |
| Checks the limit after the cache, or after asking the engine | Hits escape the limit, and refused requests still reach the engine | `h22`, `h23` |
| A `PUT` that writes the new amount into the kept price instead of deleting it | The engine may adjust a price, so the next read must ask it | `v7` |
| Deletes the kept price before the engine accepted the write | A refused write still drops the price | `h34` |
| Single flight that keeps a failed fetch in the map, or lets waiters retry on their own | Later requests get the old failure, or a crowd in an outage hammers the engine | `h6`, `h38` |
| Keeps a price only for `max-age`, ignoring `stale-while-revalidate` | A hot price that expires is a miss, and its request waits for the engine | `v9` |
| Keeps a stale price with no end | A price shown long after the engine allowed | `h51` |
| A `PUT` that marks a hot price stale instead of deleting it | The next request shows the old price | `h53` |

**Edge cases.**

- `Cache-Control` may carry `public` and spaces, in any order, and a price with no header is kept for 30 s (`v2`, `h4`).
- A price good for 1 s is kept for that second and gone after it (`h9`, `v3`).
- One price serves every client: the cache is not per API key, while the limit is (`h8`, `h21`).
- A burst of two clients interleaved lets 5 of each through (`h24`).
- An API key of 65 characters, or with a space, is no key (`h26`, `h27`), and a `PUT` with none is 401 before its body is read (`h42`).
- `amount_cents` of `"14.00"` is text, 0 is below the range, and a JSON array is not an object (`h31` to `h33`).
- Requests that miss together share whatever the engine answered, an unknown SKU or an outage included, and two SKUs never wait for each other (`h37` to `h39`).
- A refresh that fails leaves the stale price showing until its stale time ends (`h50`).
