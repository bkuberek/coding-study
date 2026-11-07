# Vendor Retry Client (TypeScript)

## Statement

The company reaches an unreliable rates vendor through one client, which today sends a request and reports what came back. Retries look easy, and they are how a small vendor problem turns into a large one: too many, too fast, at the same moment, for things that can never work, or twice for something that should only happen once.

Each level adds one rule that real clients need, and the hidden cases check the exact moment of every attempt, so the timing has to be right and not merely plausible. The project runs on a virtual clock, so a wait takes no real time.

The vendor, its paths and its numbers are invented.

## Input

- `new RatesClient()`: a client with nothing scripted. Each test gets a new one.
- `scriptVendor(steps)`: adds steps to the vendor's script, which each attempt uses up in order, one step per attempt, whichever call makes it. Past the end of the script, an attempt gets `200 10`.
- `method`: `GET` or `POST`.
- `path`: the path it asks for.
- `idempotencyKey`: a key the vendor can use to spot a repeated request, `""` for none.

At level 1 a step is `<status> <latencyMs>`: `503 50` answers 503 after 50 ms. Later levels add other kinds of step.

## Output

`call` returns a promise of JSON text with sorted keys: how many attempts it made, how it ended, and the status of the last attempt, or `null` when that attempt got no status.

```json
{"attempts":3,"outcome":"ok","status":200}
```

`attempts()` returns what the vendor has seen, oldest first, one line per attempt: when it started in virtual milliseconds, the method, the path, and the key if there was one. `0 GET /rates` and `110 POST /orders key=k1`.

## Project

`cstudy start` copies the client into `projects/vendor-retry-client-typescript/`:

- `src/ratesClient.ts`: the class `RatesClient`, exported by name, which must stay there.
- `src/vendor/scriptedVendor.ts`: `ScriptedVendor`, whose `send` starts an attempt and returns a promise of its answer. It stands for the network, so leave it as it is.
- `src/timing/`: `sleep`, and `JitterSource` with `ScriptedJitter`.
- `tests/vendor.test.ts`: tests of those pieces, `tests/virtual-clock.ts`, the grader's clock, which must stay as it is, and `tests/level-<n>.test.ts`: the examples of each open level as `node:test` tests, written when the level opens and never rewritten.
- `README.md`, `package.json` and `tsconfig.json`.

`cstudy test vendor-retry-client-typescript` runs your tests, and so does `node --test` in the project folder; either run is feedback only, and `cstudy test --typecheck` also type-checks the project. `cstudy submit vendor-retry-client-typescript` grades every case of the open levels, hidden ones included, and opens the next level when they all pass. Each submission grades the earlier levels again, so a later change must keep their rules. Node runs the files by stripping their types, so write no `enum`, no `namespace` and no constructor parameter properties, and import your own files with their `.ts` extension.

Read the time only with `Date.now()`, and wait only with `setTimeout` or `sleep`. Nothing else moves on the virtual clock.

## Level 1: Exponential backoff

Today a 503 is the caller's problem. Make the client try again.

- An answer with a status from 200 to 299 ends the call with the outcome `ok`.
- A 503 means try again, up to **6 attempts** in all. When the last one is also a 503, the outcome is `exhausted`.
- The wait after the `n`th failed attempt is `min(100 * 2^(n-1), 1000)` ms: 100, 200, 400, 800, then 1000. It is counted from when that attempt's answer arrived.
- A key goes out on every attempt of the call.

Calls do not share a count: each call starts its own backoff from the beginning.

### Example 1

<!-- case: ex1 -->

The first attempt answers at 50, and the second starts 100 ms later, at 150. It answers at 200, and the third starts 200 ms later, at 400.

### Example 2

<!-- case: ex2 -->

Six attempts, and the wait before the sixth is capped at 1000 ms, where the doubling would have made it 1600.

## Level 2: Jitter you can test

When a vendor comes back, every client that was waiting for it comes back at the same moment, unless each waits a different time. So each wait now takes a random share of the level 1 number, which is now its **ceiling**:

`wait = floor(fraction * ceiling)`

The fraction comes from a `JitterSource`, never from `Math.random`: the client gets the source passed in, so that a test can script it. `scriptJitter(fractions)` adds fractions to a `ScriptedJitter`, which answers 1 when it runs out, so with nothing scripted the waits are the ceilings.

Draw one fraction each time a wait is about to start, and at no other time: not for a first attempt, not on a success, and not after the last attempt, where no wait follows.

### Example 1

<!-- case: ex3 -->

Half of 100 is 50, and a quarter of 200 is 50.

### Example 2

<!-- case: ex4 -->

A fraction of 0 retries in the same millisecond. The next call draws 0.999, and 0.999 of 100 rounds down to 99.

## Level 3: Only what is retryable

Retrying a 404 wastes time. Retrying a payment that might have gone through can take someone's money twice. Whether a retry is safe depends on the request as well as on what came back.

A **repeatable** request is a `GET`, or a `POST` with a key. Two new kinds of step arrive:

- `reset <latencyMs>`: `send` rejects with `ConnectionReset` after that long. The request never reached the vendor, and the attempt has no status.
- `hang`: `send` never settles. An attempt that has no answer after **1000 ms** has timed out, and it has no status, even if an answer comes later. A step such as `200 1500` is therefore a timeout too.

| What the attempt got | Repeatable request | `POST` with no key |
|----------------------|--------------------|--------------------|
| Status 200 to 299 | `ok` | `ok` |
| Status 429 | Retry | Retry: the vendor refused before doing anything |
| Status 500, 502, 503 or 504 | Retry | `unknown` |
| Any other status | `rejected` | `rejected` |
| `reset` | Retry | Retry: it never got there |
| Timeout | Retry | `unknown` |

`unknown` means the client cannot say whether it happened, and only the caller can decide what to do about that. It is not the same as `rejected`, which means it did not happen. All of these rules hold for an attempt at any point in a call, and `exhausted` still ends a call whose last attempt would have been retried.

### Example 1

<!-- case: ex5 -->

The vendor said no, and it will say no again.

### Example 2

<!-- case: ex6 -->

The `POST` with no key got a 503, and may have done the work, so it stops. The next `POST` has a key, so the client can send it twice, and the vendor can tell.

## Level 4: Retry-After

A step can carry the header: `429 10 retry-after=2`. `VendorAnswer.retryAfter` holds its text, or `null`.

- On a 429 or a 503 that the table above retries, a whole number of seconds from 0 replaces the computed wait: wait exactly that long, whatever the ceiling, and draw no fraction. The header counts seconds.
- A value that is not a whole number of seconds is no value, so the usual computed wait applies. So does a missing header. Every other status ignores the header.
- The attempt still counts as a failed one, so the next computed wait is the ceiling for that many failed attempts.
- The vendor asked this client to stay away, so **no attempt of any call starts before the wait ends**. A new call waits, and so does a call that wakes up from its own backoff. A shorter wait never shortens a longer one that is already running.

### Example 1

<!-- case: ex7 -->

The vendor asked for 2 seconds, so the next attempt starts at 2010.

### Example 2

<!-- case: ex8 -->

The first 429 has no header, and the second has one that means nothing. Both back off as usual.

## Level 5: A deadline budget

A caller has a limit of its own, so a retry that outlives it does nobody any good. `setDeadline(budgetMs)` gives every later call a budget, counted from when that call starts, time spent waiting included. A client with no deadline set has no limit.

- An attempt's timeout is 1000 ms or what is left of the budget, whichever is shorter. An attempt cut this way is a timeout, so the table applies to it.
- Before any wait, computed or asked for: if the wait would end at or past the deadline, the call ends at once with `deadline_exceeded`, without waiting. A fraction drawn for that wait stays drawn.
- `status` is the last attempt's, or `null` if the call made none.

A `POST` with no key whose attempt was cut still answers `unknown`, because the vendor might have done the work. So does the table's rule on any other attempt: `deadline_exceeded` only ever replaces a retry.

### Example 1

<!-- case: ex9 -->

After the third attempt the next wait is 400 ms, which would end at 730, past the budget of 500. The call ends right there, at 330, instead of sleeping and failing later.

### Example 2

<!-- case: ex10 -->

The second attempt starts at 1100, with 100 ms of budget left, so it is cut at 1200.

## Level 6: A circuit breaker

A vendor that is down gets no better for being called, and every call that waits for it ties up something on our side. `setBreaker(failures, cooldownMs)` turns on a breaker for the whole client. A client with no breaker set has none.

- A **failure** is an attempt that ended in status 500, 502, 503 or 504, a reset or a timeout. Any other answer, a 429 or a 404 included, is a vendor that is alive, and it sets the count back to 0.
- After `failures` failures in a row, across all calls, the breaker **opens** for `cooldownMs`, counted from the failure that opened it. The call whose attempt opened it ends at once with `circuit_open`, with no wait. If the table says `unknown` for that attempt, the call ends with `unknown` instead, because the caller still needs to know that.
- While the breaker is open, no attempt starts. A call that reaches the point of starting an attempt ends with `circuit_open`, at once: a new call with `attempts` 0, and a call that was waiting in its backoff with what it had so far.
- When the cooldown is over, the next attempt is a **probe**, and only one may be out at a time: other calls still end with `circuit_open` while it is. A probe that is a failure opens the breaker again for a whole new cooldown, from that failure, and its call ends with `circuit_open`. Any other answer closes the breaker with a count of 0, and its call goes on by the usual rules.

### Example 1

<!-- case: ex11 -->

Two failures in a row open it, at 120. The next call fails at once, sends nothing, and takes no time.

### Example 2

<!-- case: ex12 -->

5000 ms later a call is allowed through, and its success closes the breaker.

## Constraints

- At most 40 calls per test, and at most 40 steps.
- Latencies are whole numbers of milliseconds from 1 to 5000.
- Fractions are from 0 to 1.
- A budget is a whole number from 1 to 1,000,000 ms. A breaker's `failures` is from 1 to 10, and its `cooldownMs` is from 1,001 to 1,000,000.
- No expected value depends on the order of two things due at the same virtual millisecond.

## Follow-ups

- A retry budget: at most 10% of this client's traffic may be retries, across all calls. Where does that go, and which outage does it protect against that the breaker does not?
- `Retry-After` can also be a date. What can go wrong when your clock and the vendor's disagree?
- A service calling this client also retries, three times, and its caller retries too. What happens to the vendor's load, and where should retries live?
- `unknown` reaches a caller who needs an answer. What API from the vendor would let it find out?

## Hints

### Hint 1

Write the wait after an attempt as a function of how many attempts have failed, and nothing else. Keep the count in the call, not in the client.

### Hint 2

Draw the jitter where the wait is computed, not at the top of the loop. Then the only question is when a wait is computed.

### Hint 3

Write the table in level 3 as one pure function of the attempt and the request. Everything else in the client is about time.

### Hint 4

A hold shared by every call is a single number: the time before which nothing may start. Check it right before each attempt, rather than only after a 429.

### Hint 5

`Promise.race` between the answer and a timer gives you the attempt's timeout. What is the timer's length, once there is a deadline?

### Hint 6

Before each attempt, ask the breaker. After each attempt, tell it. Those two calls can hold every rule of level 6, except for what comes first when the attempt is both a failure and `unknown`.
