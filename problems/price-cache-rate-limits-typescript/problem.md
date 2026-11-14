# Price Cache and Rate Limits (TypeScript)

## Statement

A shop publishes its prices through a public API, for its own apps and for the comparison sites that list its products. Behind the API sits the pricing engine, which works each price out from costs, stock and promotions, and takes its time: about 200 ms for a price, and over a second for some. On a quiet day the API can ask the engine every time. On the day a comparison site runs a script that asks for the same lamp a thousand times a minute, the engine falls over, and every client with it.

Build the API's protection in levels, on a store that speaks Redis's protocol. It keeps prices for as long as the engine says they stay good, limits each client to a few requests a second however hard it pushes, drops a price when someone sets a new one, sends a crowd that misses the same price to the engine once, and finally keeps the shop's hottest prices from sending a crowd to the engine at all when they expire. `cstudy` runs your app, the store and a stand-in for the engine in a Docker sandbox, and judges your app by what it answers over HTTP, by bursts of requests sent at the same moment, and by counting the requests the engine received. The shop, its products and its numbers are invented.

## Input

HTTP requests: `GET /prices/{sku}` for a product's price, and from level 3 `PUT /prices/{sku}` with a JSON body to set one. Every request carries the client's key in the `X-Api-Key` header. Each level says what it adds.

## Output

JSON, always with `Content-Type: application/json`, except for a `204`, which has no body. A refusal is `{"error": "<code>"}`, with the codes each level names. Your app reads its port from `PORT` and listens on all interfaces inside the container (`0.0.0.0`), and `GET /health` answers 200 once it is ready.

## Project

`cstudy start` copies the service into `projects/price-cache-rate-limits-typescript/`, and `cstudy dev` runs it with its store and the engine. Node runs the files by stripping their types, so write no `enum`, no `namespace` and no constructor parameter properties, and import your own files with their `.ts` extension.

- `src/server.ts`: the routes, and where the server starts. It answers `GET /prices/{sku}` by asking the engine every time, and 501 to `PUT`.
- `src/pricing.ts`: the engine's client, at `PRICING_URL`. Its contract is in `vendors/pricing/API.md`.
- `src/store.ts`: the store's client, at `REDIS_URL`, from the `redis` package. The store is Valkey, the open-source fork of Redis, which answers the same commands, Lua scripts and transactions included.
- `scripts/bootstrap.ts` and `scripts/reset.ts`: check the store answers before your app starts, and empty it before a case that starts fresh. You should not need to change them.
- `tests/`: your tests, run by `cstudy test`, with `tests/pricingScenario.ts` to set one of the engine's visible scenarios and count the requests it received.
- `.env`: what your app reads, written by `cstudy start` from the problem's settings. Your app's environment already holds it.

`cstudy test` starts a sandbox, runs your tests beside the app, and then the visible cases of your open levels. `cstudy submit` grades every case of the open levels, hidden ones included, and opens the next level when they all pass. Each submission grades the earlier levels again, so a later change must keep their answers. Every case starts with an empty store and your app started again. To look inside the store while `cstudy dev` runs, `docker ps` shows its container, whose name ends in `-store-1`, and `docker exec -it <that name> valkey-cli` opens a shell on it.

## Level 1: Cache-aside

`GET /prices/{sku}` answers 200 with the price, as the engine gives it:

```json
{"sku": "lamp", "amount_cents": 1250, "currency": "EUR"}
```

Keep each price in the store, and answer from there while it is good, without asking the engine. How long a price stays good is the engine's `Cache-Control` header:

| The engine says | Keep the price |
|-----------------|----------------|
| `max-age=<seconds>` | That many seconds |
| `max-age=0`, or `no-store` | Not at all |
| No `max-age` and no `no-store` | 30 seconds |

The header may hold other directives, such as `public`, in any order. The store must forget a price once its time is up by itself: give each key its expiry.

Every 200 says where its price came from, in the header `X-Cache`: `hit` when it came from the store, and `miss` when your app asked the engine for it.

| The engine | Status | Body |
|------------|--------|------|
| Answers 404 | 404 | `{"error": "unknown_sku"}` |
| Answers any other failure, or none within 5 s | 502 | `{"error": "pricing_unavailable"}` |

A failure is never kept: the next request asks the engine again. Every request already carries an `X-Api-Key`, which level 2 reads.

### Example 1

<!-- case: v1 -->

Nothing is kept yet, so the price comes from the engine, which received one request for it.

### Example 2

<!-- case: v2 -->

The lamp is good for 60 s, so the second request is answered from the store, and the engine still received one request.

### Example 3

<!-- case: v3 -->

The kettle is good for 1 s. The case asks for the anvil in between, which takes the engine 1.2 s to price, so by the third request the kettle has expired and the engine is asked again.

## Level 2: Rate limits

Each client may send at most 5 requests a second, counted by its `X-Api-Key`. Every request to `/prices` counts, whether it was answered from the store or not, and the limit is checked before anything else is done.

| Request | Status | Body |
|---------|--------|------|
| No `X-Api-Key`, or one that is not 1 to 64 letters, digits, `-` or `_` | 401 | `{"error": "missing_api_key"}` |
| Over the client's limit | 429 | `{"error": "rate_limited"}` |

A 429 carries `Retry-After`: the whole seconds until the client's next request would go through, rounded up, so `1` here. A refused request takes nothing from the client's allowance, and never reaches the store's prices or the engine. One client's limit never touches another's.

Two ways meet the rule, and either is fine: a sliding window that counts the requests of the last second and lets one through while it holds fewer than 5, or a token bucket that holds 5 tokens and gains one every 200 ms. Both let a burst of 5 through at once, and both give a client that waited a second its 5 again.

The cases send bursts of up to 20 requests at the same moment. Reading a count, deciding, and writing it back is the bug: between your read and your write, every other request of the burst read the same count. The check and the update must be one step in the store: a Lua script, which the store runs alone with nothing in between, or a `MULTI` transaction of commands that decide by themselves.

### Example 1

<!-- case: v4 -->

The request names no client, so it is refused before anything else.

### Example 2

<!-- case: v5 -->

The lamp is first kept by another client. Then client `v5` asks for it five times, and its sixth request within the second is refused.

### Example 3

<!-- case: v6 -->

A burst's example shows the request it repeats and the statuses expected, which can come back in any order.

## Level 3: Writes and stampedes

`PUT /prices/{sku}` sets a price through the engine:

```json
{"amount_cents": 1400}
```

`amount_cents` is a whole number from 1 to 10000000. Your app sends it to the engine's `PUT`, and once the engine has answered 204, deletes the kept price and answers 204 with no body. The engine may adjust a price it is given, so the next `GET` asks the engine. A write the engine refuses changes nothing, the kept price included.

| Request | Status | Body |
|---------|--------|------|
| A body that is not a JSON object, or `amount_cents` missing or breaking its rule | 400 | `{"error": "invalid_request"}` |
| The engine answers anything but 204, or nothing within 5 s | 502 | `{"error": "pricing_unavailable"}` |

A `PUT` needs an `X-Api-Key` and counts toward the limit as a `GET` does, and both are checked first.

Many clients often miss the same price at the same moment: the comparison sites refresh their listings on the hour. Each of those requests finding nothing and asking the engine is a stampede, and it is what sends the engine down. Requests that miss the same price while it is being fetched wait for that one fetch and share its answer, whatever it is: a price, an unknown SKU or a failure. Prices of different SKUs never wait for each other. Your app runs as one process, so a promise kept per SKU while its fetch runs is enough; a lock in the store also works. A request that waited for a fetch says `X-Cache: miss`.

### Example 1

<!-- case: v7 -->

The engine answers 1250 for the lamp at first, and 1400 once it has been set.

### Example 2

<!-- case: v8 -->

Ten clients ask for the desk at once, with nothing kept: each gets its price, and the engine received one request.

## Level 4: Hot prices

One product a week is on promotion, and its price is asked for many times a second. The engine marks such a price as short-lived and allows it to be shown for a while after: `Cache-Control: max-age=1, stale-while-revalidate=30`.

Single flight already sends the engine one request when the price expires, but every request in the meantime waits for that slow answer. Instead, once `max-age` has passed and for as many more seconds as `stale-while-revalidate` says, answer the old price at once, with `X-Cache: stale`, and fetch the new one in the background: one fetch per SKU at a time, however many requests found the price stale. A fetch that succeeds keeps the new price under its own `Cache-Control`. One that fails changes nothing, so the old price is shown, and fetched again, until its stale time is up. After that it is a miss, as before.

A price without `stale-while-revalidate` behaves as in level 1. A `PUT` deletes the price, stale time and all, so the next request waits for the new one.

### Example 1

<!-- case: v9 -->

The clock is good for 1 s and may be shown for 30 more. The first anvil lets it expire, so the third request gets the old price at once and starts the fetch, which answers 4200 good for 60 s. The second anvil gives that fetch time to finish.

### Example 2

<!-- case: v10 -->

Ten clients find the clock stale at once: each gets the old price, and the engine received one more request.

## Constraints

- A store that speaks Redis's protocol, through `REDIS_URL`, with the `redis` client. It starts empty for every case, and nothing on disk outlives a stack.
- At most 5 requests a second per API key, and bursts of up to 20 requests at once; a case has 10 s for all its requests, and 15 s when it waits for the anvil.
- Every answer of a case that repeats must be right on every run: a race that loses one time in three still fails.
- The engine takes about 200 ms for a price, and 1.2 s for the anvil.

## Follow-ups

- The store goes down. Should the cache fail open, asking the engine for every request, or closed? And the limiter: letting everyone through protects your clients, refusing everyone protects the engine. Which would you pick for a public API, and how would you stop each request from waiting for the store's timeout?
- Three copies of the service run behind a load balancer. Which of your levels still hold, and what does single flight need from the store then?
- A `GET` misses, asks the engine, and a `PUT` deletes the key while that request waits. Then the `GET` stores the old price. How would you keep a write from being undone that way?
- A client spreads its requests across a hundred API keys. What would you limit by instead, and what does that cost the honest clients behind one office's address?
- Thousands of prices were all kept at the same moment with the same `max-age`. What happens when they all expire together, and how would a little randomness help?
- A script asks for SKUs that do not exist, each once. Single flight does not help. How would you keep those requests from all reaching the engine?
- Stale-while-revalidate still lets the first request after the stale time wait. When would you refresh a hot price before it expires, and how would you know it is hot?

## Hints

### Hint 1

Read `Cache-Control` by splitting it on commas, trimming each part, and looking for `no-store` and `max-age=`. `SET key value EX seconds` keeps a value and gives it its expiry in one command. Store the engine's body as it came, and you can send it back as it is.

### Hint 2

A limit check that reads with `GET`, compares, and then writes passes every case that sends one request at a time, and fails the bursts. Each command alone is atomic; a check made of several is not, unless it is a Lua script sent with `EVAL`, which the store runs whole before any other command.

### Hint 3

A sliding window fits a sorted set per client: each request a member scored by its time. In one script, drop the members older than a second (`ZREMRANGEBYSCORE`), count the rest (`ZCARD`), and only if there are fewer than 5 add this one (`ZADD`) and give the key an expiry (`PEXPIRE`), so an idle client's key goes away. `redis.call('TIME')` inside the script gives one clock for every copy of your app. Each member must be unique, even for two requests in the same millisecond.

### Hint 4

Single flight is a `Map` from SKU to the promise of its fetch. A request that finds a promise there awaits it; the one that finds none starts the fetch, puts its promise in the map, and removes it once it settles, whatever the outcome. Put the store's write inside that promise, so a request that comes right after finds the price kept.

### Hint 5

For level 4, keep one key per price with a TTL of `max-age` plus `stale-while-revalidate`, and store beside the body the moment it stops being fresh. A read before that moment is a hit, a read after it is stale. A background fetch is the same single flight, started without awaiting it, and catching its failure so nothing is left unhandled.
