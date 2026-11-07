# Vendor Retry Client (TypeScript): Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | O(a) per call | O(a) | default answer: one loop that owns the time, a pure table of verdicts, a hold and a breaker shared by the client |

Here `a` is the number of attempts in the log. A call makes at most 6.

## How the project grows level by level

| Level | New requirement | What the code adds |
|-------|-----------------|--------------------|
| 1 | Backoff | A loop in `src/retry/retryingCaller.ts` and `backoffDelay` in `src/retry/policy.ts` |
| 2 | Jitter | A `JitterSource` passed in, and one `next()` where the wait is computed |
| 3 | What is retryable | `verdictOf`, a pure table, and a `Promise.race` against a timer |
| 4 | `Retry-After` | `retryAfterDelay`, and `#holdUntil`, checked before every attempt |
| 5 | Deadline | `deadlineAt` per call: a shorter timer, and a check before each wait |
| 6 | Breaker | `src/retry/breaker.ts`, asked before each attempt and told after it |

## Approach: reference (One retry loop over a table of verdicts with a client-wide hold and a breaker)

### Intuition

A retry is a load decision and a safety decision, and most retry code treats it as an error-handling detail.

**The load side.** Doubling the wait gives a struggling vendor room, and jitter stops every client from returning at the same moment, which is why the fraction matters as much as the exponent. `Retry-After` is the vendor telling you the number, so you stop guessing, and it applies to the whole client, not just the call that happened to get the header: otherwise the rest of your traffic walks straight into the limit. A breaker is the end of that line of thought: past some point the kindest thing to send is nothing.

**The safety side.** A 503 or a timeout does not mean nothing happened. It means you don't know, which is why a `POST` with no key cannot be retried, and why its outcome is `unknown`, a word you owe the caller. A 429 and a connection reset are different: the vendor did not do the work, so they are safe for anything.

**The time side.** Every wait has to fit in what the caller still has. A client that sleeps past the deadline and then fails has wasted the caller's time, and an attempt that outlives the budget has done the same with an extra step.

Separate these three, and the code is short. `policy.ts` holds the safety side as pure functions, and the loop holds the time.

### Say it out loud

"A retry can make an outage worse, so I want to be explicit about which failures I retry. A 4xx won't change. A 429 or a connection failure never did the work, so they're always safe. A 5xx or a timeout is ambiguous: the vendor may have done it. So I only retry those for reads or for writes with an idempotency key, and otherwise I tell the caller the outcome is unknown, which is different from failed.

"For timing: exponential backoff with full jitter, so clients don't all come back together. The jitter source is injected, because I want tests that assert exact times. `Retry-After` beats my number when it's there, and it holds the whole client. I'd also make sure I'm reading seconds.

"There's a deadline across attempts, not just per attempt. Each attempt's timeout is capped by what's left, and if a wait would end past the deadline I fail now, rather than sleeping and then failing.

"And a breaker on top: consecutive failures open it, then one probe at a time. A 404 doesn't count, because that's a healthy vendor saying no. Without the single probe, the moment the cooldown ends everything rushes in, and I've built the outage I was trying to avoid."

### Algorithm

1. Work out `deadlineAt` from the budget, if there is one.
2. Loop. If a hold is running, stop with `deadline_exceeded` when it would end at or past the deadline, and otherwise sleep until it ends, and look again.
3. Ask the breaker. If it says no, stop with `circuit_open`.
4. Make the attempt, racing the answer against a timer of `min(1000, what is left)`. Count it. Tell the breaker whether it was a vendor failure.
5. Ask `verdictOf`. Anything but `retry` ends the call with that outcome, which is what puts `unknown` ahead of `circuit_open`.
6. If the breaker is now open, stop with `circuit_open`. If this was the sixth attempt, stop with `exhausted`.
7. If the vendor asked for a wait, push the hold out, never back, and go round again: step 2 handles the deadline.
8. Otherwise draw one fraction, compute the wait, stop with `deadline_exceeded` if it would end at or past the deadline, and sleep.

### Design

| File | Responsible for |
|------|-----------------|
| `src/ratesClient.ts` | `RatesClient`: wiring, and the JSON |
| `src/retry/retryingCaller.ts` | The loop: the order of the checks, all of the waiting, and the hold. It asks about everything else |
| `src/retry/policy.ts` | Pure functions: the verdict table, what a vendor failure is, the backoff and the header. A review of retry behavior reads this page |
| `src/retry/breaker.ts` | The breaker's states. It reads the clock, and knows nothing about HTTP |
| `src/vendor/scriptedVendor.ts` | The network. Unchanged |
| `src/timing/sleep.ts`, `src/timing/jitter.ts` | The clock's and the random source's seams. Unchanged |
| `tests/policy.test.ts` | The table and the arithmetic, without a clock |

The race leaves the vendor's timer running after a timeout, which models a real request you have stopped waiting for: the vendor may still be working on it. In real code you would also abort it, with an `AbortController`, so that the socket does not outlive the attempt. And the client clears its own timer in a `finally`, because a timer that stays armed after the answer keeps a real process alive and leaks a little work per call.

### Next in production

- Put a retry budget on the client: retries may be, say, 10% of requests. A breaker opens on failures in a row, and a budget also limits the slow bleed where a third of calls fail.
- Retry at one layer only. If three layers each try 3 times, one failure is 27 attempts at the vendor. Say which layer owns retries, and make the others pass failures through.
- Export the numbers: attempts per call, retry rate, breaker state changes, and time spent held. Alert when the breaker opens. An open breaker is an incident, and a silent one looks like your own outage.
- Keep a breaker per endpoint or per vendor region, not one for everything, so that one bad path does not take down the rest.
- Propagate the deadline. Pass what is left to the next service, in a header, so that it does not work on a request that nobody is waiting for any more.
- Abort the request on timeout, with an `AbortController`, and clear what you can. A timed-out request that stays open holds a socket from a limited pool.
- Ask the vendor for an idempotency key if it doesn't support one, or for a way to look up a request by your own id. That is the only real answer to `unknown`.

### Correctness

A call's count and deadline are local variables, so calls cannot disturb each other's backoff. The hold and the breaker are client fields, because those rules are about the client.

A wait is computed in exactly one place, and that is the only place a fraction is drawn. So a first attempt, a success, the last attempt and an asked-for wait all draw nothing. The cap applies before the fraction, so the fraction scales the capped ceiling.

Every attempt's timer is at most what is left of the budget, so no attempt can run past the deadline. Every wait is checked before it starts, so no wait ends at or past it, and a call never sleeps to fail. So `@now` at the end of a call with a budget is at most the budget.

Step 5 comes before 6, so an ambiguous attempt always reports `unknown`, even when it is the one that opened the breaker or used up the last chance. That is on purpose: a caller told `circuit_open` would assume that nothing happened.

The breaker is asked immediately before each attempt, so a call waiting in backoff cannot reach the vendor after it opened. `admit` sets `#probing` synchronously, with no `await` before the attempt starts, so two calls cannot both become the probe. Attempts last at most 1000 ms, which is below any cooldown in this problem, so no attempt from before the breaker opened can come back during a probe and be taken for its result.

### Complexity

- Time: O(a) per call — a fixed amount of work per attempt, and at most 6 attempts. The waiting takes virtual time, and no real time.
- Space: O(a) — one line in the attempt log per attempt; a call holds a few numbers.

### Trade-offs

- **Full jitter against equal jitter.** Full jitter (`fraction * ceiling`) spreads clients the most, and it can retry almost at once. Equal jitter keeps a floor of half the ceiling and spreads them less. Either is defensible, and no jitter is not.
- **Backoff measured from the answer against the start of the attempt.** From the answer is simpler to reason about and gentler on a slow vendor.
- **Counting attempts against counting calls in the breaker.** Attempts react faster, since one call can open it. Calls give a steadier signal, and let retries hammer a dead vendor for longer.
- **A 429 as a failure.** A vendor that is rate-limiting you is up, and opening the breaker throws away capacity it would have given you. If 429s are constant, the fix is your request rate, not the breaker.
- **Failing fast with no fallback.** `circuit_open` is honest, but a cached rate might serve the caller better. That is a product decision, and the client should make it possible without deciding it.

### Pitfalls and edge cases

Each wrong approach below was run as a one-line change on the reference, through `cstudy submit`, and each fails the cases named with it.

**Backoff.**

- **Linear backoff, or no cap.** Caught by `ex2`, `h9` and `h10`.
- **An exponent off by one.** The first wait is then 200. Caught by `ex1` and `h4`.
- **Counting the wait from when the attempt started.** A slow vendor then gets less room, exactly when it needs more. Caught by `ex1` and `h5`.
- **Keeping the failure count on the client.** One call's failures lengthen another's waits. Caught by `h4` and `h7`.
- **Sending the key on the first attempt only.** The retry is then a new request to the vendor. Caught by `h6` and `h23`.
- **A seventh attempt.** Caught by `ex2`, `h9` and `h19`.

**Jitter.**

- **`Math.random()` in the client.** Nothing can test it. Caught by `ex3`, `h8` and `h10`.
- **Taking the fraction before the cap.** `0.5 * 1600` is 800, where the rule gives 500. Caught by `h10`.
- **`Math.round` in place of `Math.floor`.** Caught by `ex4` and `h13`.
- **Drawing on the first attempt.** Every later fraction is then one off. Caught by `ex3`, `h8` and `h12`.
- **Drawing after the last attempt.** No wait follows it, and the next call gets the wrong fraction. Caught by `h9`.
- **Drawing for a wait the vendor asked for.** Caught by `h30`.

**What is retryable.**

- **Retrying every `POST`.** A timeout on a payment is not a reason to send it again. Caught by `ex6`, `h22` and `h25`.
- **Retrying no `POST`, key or not.** The key is there to make it safe. Caught by `h6`, `h23` and `h43`.
- **`status >= 500`.** A 501 will not change. Caught by `h15`.
- **Retrying every failure.** Caught by `ex5`, `h15` and `h27`.
- **Reporting `rejected` instead of `unknown`.** The caller then believes that nothing happened, and may do it again. Caught by `ex6`, `h22` and `h28`.
- **Treating a 429 or a reset like a 503 for a bare `POST`.** They are the cases where the vendor certainly did not do the work. Caught by `h17`, `h20` and `h35`.
- **Accepting an answer after the timeout.** Caught by `h21`, `h24` and `h25`.

**`Retry-After`.**

- **Reading the header as milliseconds.** Caught by `ex7`, `h30` and `h39`.
- **Capping the vendor's number.** Caught by `ex7` and `h31`.
- **Honouring it on any status that retries, or on a 429 alone.** Caught by `h37` and `h33`.
- **`Number(value)` to parse it.** `-1` and `1.5` and `""` all come out as numbers. Caught by `h36`.
- **Waiting in this call only.** The rest of the client walks into the limit. Caught by `h38`, `h40` and `h41`.
- **Holding new calls only.** A call already retrying is the worst offender, and it then ignores the header. Caught by `ex7` and `h40`.
- **Letting a shorter wait replace a longer one.** Caught by `h41`.
- **Not counting an asked-for wait as a failed attempt.** The next computed wait is then too short. Caught by `h30`.

**The deadline.**

- **A full timeout whatever is left.** The call outlives its budget. Caught by `ex10`, `h42` and `h43`.
- **Sleeping, then noticing.** The caller waits for a failure you already knew about. Caught by `ex9`, `h44` and `h51`.
- **Allowing a wait to end exactly at the deadline.** There is no time left for what it was waiting for. Caught by `h44` and `h51`.
- **Sleeping through a hold past the deadline.** Caught by `h46` and `h49`.
- **Letting `deadline_exceeded` replace `unknown`.** It hides that the request may have happened. Caught by `h42`.
- **Starting the budget when the client starts, or at the first attempt.** A budget is the caller's, from when it called. Caught by `h48` and `h50`.
- **Checking the deadline against the ceiling, before the fraction is drawn.** It gives up on waits that fit. Caught by `h51`.

**The breaker.**

- **Counting 4xx or 429 as failures.** A healthy vendor that says no opens the breaker. Caught by `h58`, `h59` and `h63`.
- **Counting failures that are not in a row.** A rare error rate eventually opens it. Caught by `h57` and `h58`.
- **Counting only statuses.** A vendor that has gone silent is the one you most want to stop calling. Caught by `h60`.
- **Letting everyone through at the end of the cooldown.** The stampede it was protecting against. Caught by `h56`.
- **`<=` on the cooldown.** Caught by `ex12` and `h54`.
- **Counting the cooldown from the first failure of the run.** Caught by `h54` and `h66`.
- **A failed probe that does not start a new cooldown.** Everything floods back at once. Caught by `h55`.
- **Keeping the old count after closing.** One more failure then reopens it. Caught by `h64` and `h65`.
- **Asking the breaker only at the start of a call.** A call in backoff sends one more attempt to a vendor that is down. Caught by `h62`.
- **Sleeping out the backoff after the failure that opened it.** Caught by `ex11` and `h54`.
- **Letting `circuit_open` replace `unknown`.** Caught by `h61`.
- Project traps: `src/ratesClient.ts` must export `RatesClient` by name; keep `tests/virtual-clock.ts` as it is; local imports need their `.ts` extension; a timer function saved before the clock started is the real one, which the clock cannot move.
