# Coworking Availability (TypeScript): Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | per request | per request | default answer: one client per vendor, each hiding its own shape and failures behind the same small interface |

## How the project grows level by level

| Level | New requirement | What the code adds |
|-------|-----------------|--------------------|
| 1 | The right answer to a wrong request | `isRealDay` in `src/dates.ts`, `refusal` and a table of routes in `src/server.ts` |
| 2 | One answer with the vendor's slots | `src/vendors/roomVendor.ts`, and `src/availability.ts`, which flattens and sorts |
| 3 | A vendor that fails | `waitBeforeRetry` and a bounded loop in the client; a rejection becomes `unavailable` |
| 4 | A second vendor | `src/vendors/annexVendor.ts` and a `RoomSource` interface, with `Promise.allSettled` in the merge |

## Approach: reference (One client per vendor behind one shape of answer)

### Intuition

The service has two very different kinds of data, and the design should let you see that. The desks are the space's own: they are always there, so nothing about a vendor can ever change what they answer. The rooms are someone else's: every call may fail, and the only honest question is what your caller sees when it does.

So a failure is a value, not an accident. A vendor that gives no usable answer goes in `unavailable`, and the caller gets a true answer about the rest, which is what "degrade" means. The request fails only when the request is wrong.

Retries are a load decision before they are an error-handling one. A 5xx often passes, so asking again is worth a little. A 429 is the vendor telling you the number, so you stop guessing and wait that long. A slow vendor is already struggling, and your caller is waiting, so you do not ask it again. Each vendor has its own answer to all of this, which is why it belongs in that vendor's client.

### Say it out loud

"Desks come from our own data, so I answer them no matter what. Rooms come from vendors, and I treat each vendor as something that can fail on any request, so its failure goes in the answer rather than becoming a 500 from me.

"For retries, I separate what is worth retrying from how long to wait. A 5xx gets a short wait and a bounded number of tries. A 429 tells me how long, so I use its number. I don't retry a timeout, since that vendor is struggling and my caller has been waiting. And I bound the total, because a retry loop with no limit is how a small vendor problem becomes a large one.

"Each vendor gets its own client with one method: a date in, slots out, or a rejection. The merge knows nothing about shapes or status codes, and `allSettled` means one vendor failing can't take another with it."

### Algorithm

1. Refuse a wrong request first: no date, not a real day, a day not on sale. Nothing has reached a vendor yet.
2. Ask every vendor at once with `Promise.allSettled`, each through its own client.
3. In a client, send the request with a limit of 1.5 s. If the answer is worth retrying, wait as long as it says and ask again, up to that vendor's limit. Otherwise take the answer as it is.
4. Check the body against the vendor's contract, and turn it into slots.
5. Fulfilled clients give slots, and rejected ones give a name in `unavailable`. Sort both, and answer with the desks.

### Design

- `src/server.ts`: the routes, as a table, so a known path with the wrong method answers 405 in one place, and `refusal`, the date rules both endpoints share.
- `src/dates.ts`: `isRealDay`, which builds the date and checks it came back unchanged.
- `src/desks.ts`: `DeskInventory`, unchanged from the starter.
- `src/availability.ts`: `roomAvailability`, the merge, which knows only `RoomSource`.
- `src/vendors/roomSource.ts`: the seam: `Slot`, `RoomSource`, the request limit and small helpers.
- `src/vendors/roomVendor.ts`: the first vendor's path, shape and retry rules, with `waitBeforeRetry` a pure function that a test can call.
- `src/vendors/annexVendor.ts`: the second vendor's day form, minutes and failures in the body.

Not graded, and worth discussing:

- **A circuit breaker.** After a run of failures, skip the vendor for a while and answer `unavailable` at once, so that a long outage costs neither the vendor's capacity nor your caller's time.
- **Caching.** Slots change slowly enough that a few seconds of cache would shield the vendor from a burst, at the price of offering a slot that has just gone. A booking must still ask the vendor.
- **A budget for the whole request.** With 3 tries and a `Retry-After`, one request can wait for seconds. A real service would give each request a deadline and stop waiting for a vendor once it would be missed.
- **A third vendor.** It means one new file and one line in `src/server.ts`, which is the point of the seam.

### Correctness

A valid day always answers 200: the desks come from local data, and `Promise.allSettled` never rejects, so no vendor's failure can reach the route. Every slot passes through its vendor's client, which rejects on any status or body outside the contract, so a broken answer never shows as an empty list. Nothing is sent for a refused date, since `refusal` runs before any client. Each client counts its own requests, so the limits hold whatever mix of failures comes.

### Complexity

- Time: per request — one to three requests to each vendor, at the same time, then a sort of the slots
- Space: per request — the vendors' answers while they are merged

### Trade-offs

Asking both vendors at once keeps one vendor's waits from adding to the other's, at the cost of always spending both vendors' capacity. A shared retry helper would save a few lines today and tie together two vendors whose rules differ, so each client keeps its own. The reference trusts the inner fields of a body that has the right outer shape, which keeps the clients short: a stricter parser would catch a vendor that breaks its contract more subtly.

`node:http` and `fetch` keep the install small and the seam visible. Express or an equivalent would do as well, added to `package.json` and the lock.

### Pitfalls and edge cases

**Wrong approaches.** Each fails a hidden case, and the failure names what it did.

| What it does | Why it is wrong | What catches it |
|--------------|-----------------|-----------------|
| No retry: one request to the vendor, and any failure is `unavailable` | Passes every "always fails" case, and gives up on a failure that would have passed | `h19`, and `h21`: `expected 2 requests, saw 1` |
| Retries a 429 after its own fixed wait, ignoring `Retry-After` | The vendor said how long, and it asks too soon | `h21`: `expected at least 950 ms from response 1 to request 2` |
| Waits one second after any 429 | Right only when the number happens to be 1 | `h22`: `expected at least 1950 ms` |
| Retries in a tight loop | Hammers a vendor that is already struggling | `v5`: the gap, and the count |
| Retries with no limit | One request costs the vendor an unbounded load | `v5`, `v6`: the count |
| Retries every failure, a 403 and a timeout included | A 403 will not change, and a slow vendor gets more load | `h25`, `v7` |
| Lets a vendor error reach the route | A vendor's bad minute becomes a 500 for a member who wanted a desk | `v5` |
| `Promise.all` around both vendors | The first to fail rejects the whole answer, so one vendor takes the other down | `h32`, `v9` |
| Treats a non-2xx as the only failure on the annex | Its failures arrive in the body of a 200 | `h35`, `h36` |
| Assumes both vendors fail alike | The annex's 5xx must not be retried, and its wait is in milliseconds, in the body | `v9`, `h34` |

**Edge cases.**

- A regular expression alone passes `2027-02-30`, and the same goes for a date parser that rolls it over to March, so the check has to build the date and compare (`h6`, `h10`).
- `if (!count)` calls a day with no desks left "not on sale". Zero is a count (`h1`).
- `date=` is a missing date, not a malformed one (`h3`).
- A 200 does not mean a usable answer: its body may be broken (`h26`) or a valid JSON document of the wrong shape, and `body.rooms ?? []` quietly reports a working vendor with no rooms (`h27`).
- An empty list from a vendor means "nothing on that day", which is not `unavailable` (`v4`).
- A slot of the annex needs its end worked out, and its times padded: `from_minute` 425 is `07:05` (`h31`).
- Validate before you call anyone. A bad date that reaches a vendor costs a request and may look like the vendor's failure (`h16`, `h29`).
- `/desks` needs no vendor, so it should not slow down or fail with one (`h30`).
