# Coworking Availability (Python): Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | per request | per request | default answer: one client per vendor, each hiding its own shape and failures behind the same small protocol |

## How the project grows level by level

| Level | New requirement | What the code adds |
|-------|-----------------|--------------------|
| 1 | The right answer to a wrong request | `parse_day` in `src/dates.py`; in `src/server.py`, `CoworkingApi` with a table of routes and `Refused`, raised before anything else happens |
| 2 | One answer with the vendor's slots | `src/vendors/room_vendor.py`, and `src/availability.py`, which flattens and sorts |
| 3 | A vendor that fails | `get` and `VendorError` in `src/vendors/__init__.py`, `ask_with_retries`, and the room vendor's `wait_before_retry`; a `VendorError` becomes `unavailable` |
| 4 | A second vendor | `src/vendors/annex_vendor.py`, the `RoomSource` protocol, and a thread per vendor in the merge |

## Approach: reference (One client per vendor behind one shape of answer)

### Intuition

The service has two very different kinds of data, and the design should let you see that. The desks are the space's own: they are always there, so nothing about a vendor can ever change what they answer. The rooms are someone else's: every call may fail, and the only honest question is what your caller sees when it does.

So a failure is a value, not an accident. A vendor that gives no usable answer goes in `unavailable`, and the caller gets a true answer about the rest, which is what "degrade" means. The request fails only when the request is wrong.

Retries are a load decision before they are an error-handling one. A 5xx often passes, so asking again is worth a little. A 429 is the vendor telling you the number, so you stop guessing and wait that long. A slow vendor is already struggling, and your caller is waiting, so you do not ask it again. Each vendor has its own answer to all of this, which is why its rules belong in that vendor's module, while the loop that applies them can be shared.

### Say it out loud

"Desks come from our own data, so I answer them no matter what. Rooms come from vendors, and I treat each vendor as something that can fail on any request, so its failure goes in the answer rather than becoming a 500 from me.

"Every way a vendor can fail ends as one exception of mine, `VendorError`: no answer in time, a status that will not change, a body that is not JSON or not the documented shape. Each client translates at its own boundary, so the merge catches exactly that and nothing else, and a bug in my own code still shows up as a bug.

"For retries, I separate what is worth retrying from how long to wait. Each vendor has a pure function that reads an answer and says how long to wait, or not to ask again. One small loop does the counting and the sleeping for both. I don't retry a timeout, since that vendor is struggling and my caller has been waiting, and I bound the total, because a retry loop with no limit is how a small vendor problem becomes a large one.

"I ask both vendors at once, each in its own thread, because their waits should not add up. A future holds either the slots or the exception, so one vendor failing can't take the other with it."

### Algorithm

1. Refuse a wrong request first: no date, not a real day, a day not on sale. `Refused` carries the reply, and nothing has reached a vendor yet.
2. Ask every vendor at once from a `ThreadPoolExecutor`, each through its own client.
3. In a client, send the request with a limit of 1.5 s. While its rules say an answer is worth retrying, sleep as long as they say and ask again, up to that vendor's limit.
4. Match the body against the vendor's contract with `match`, and turn it into `Slot`s. Anything else raises `VendorError`.
5. A future's result gives slots, and a `VendorError` gives a name in `unavailable`. Sort both, and answer with the desks.

### Design

- `src/server.py`: `CoworkingApi`, every answer from a method and a target, with the routes as a table, so a known path with the wrong method answers 405 in one place; `Refused`, the date rules both endpoints share; and `Handler`, which only moves HTTP in and out, so a test or another server could drive the API without it.
- `src/dates.py`: `parse_day`, a pattern for the form and then `date.fromisoformat` for the day.
- `src/desks.py`: `DeskInventory`, unchanged from the starter.
- `src/availability.py`: `room_availability`, the merge, which knows only `RoomSource` and `VendorError`.
- `src/vendors/__init__.py`: the seam: `Slot`, the `RoomSource` protocol, `VendorError`, `get` with the request limit, and `ask_with_retries`, the loop both vendors share.
- `src/vendors/room_vendor.py`: the first vendor's path, shape and retry rules, with `wait_before_retry` a pure function that a test can call.
- `src/vendors/annex_vendor.py`: the second vendor's day form, minutes and failures in the body.

Not graded, and worth discussing:

- **A circuit breaker.** After a run of failures, skip the vendor for a while and answer `unavailable` at once, so that a long outage costs neither the vendor's capacity nor your caller's time.
- **Caching.** Slots change slowly enough that a few seconds of cache would shield the vendor from a burst, at the price of offering a slot that has just gone. A booking must still ask the vendor.
- **A budget for the whole request.** With 3 tries and a `Retry-After`, one request can wait for seconds. A real service would give each request a deadline and stop waiting for a vendor once it would be missed.
- **A third vendor.** It means one new module and one line in `main`, which is the point of the seam.
- **asyncio.** `asyncio.gather(..., return_exceptions=True)` would ask the vendors without threads, but the standard library has no asynchronous HTTP client, so it brings a dependency, and with two vendors per request a thread each costs nothing worth saving.

### Correctness

A valid day always answers 200: the desks come from local data, and every way a vendor can fail ends as a `VendorError` inside its client, which the merge turns into a name in `unavailable`. Every slot passes a `match` against its vendor's contract, so a broken answer never shows as an empty list. Nothing is sent for a refused date, since `_on_sale` runs before any client. Each client counts its own requests through `ask_with_retries`, so the limits hold whatever mix of failures comes.

### Complexity

- Time: per request — one to three requests to each vendor, at the same time, then a sort of the slots
- Space: per request — the vendors' answers while they are merged

### Trade-offs

Asking both vendors at once keeps one vendor's waits from adding to the other's, at the cost of always spending both vendors' capacity, and of two threads for each request. The retry loop is shared and the rules are not: `ask_with_retries` only counts and sleeps, and each vendor's `wait_before_retry` reads its own kind of answer, a status and a header for one, a body for the other. Sharing the rules too would tie together two vendors that agree on nothing.

`match` with mapping patterns, such as `{"rooms": list(rooms)}`, checks the whole shape of a body in about as many lines as trusting it would take, so the clients reject a vendor that breaks its contract in a nested field, not only at the top.

`urllib.request` applies its timeout to each wait on the socket, not to the request as a whole: a vendor that sends its answer one byte a second would be waited for. The mock vendors are slow before their first byte, where the two are the same. A deadline for the whole request needs a thread to wait on, or a client library that has one.

`http.server` and `urllib` keep the install at pytest alone and the seam visible. A framework would route and serialize for you, added to `pyproject.toml` and the lock; the date rules, the retry rules and the merge would not change.

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
| Calls `result()` on each future with nothing around it, or asks the vendors one after the other in one `try` | The first to fail raises out of the merge, so one vendor takes the other down | `h32`, `v9` |
| Treats a non-2xx as the only failure on the annex | Its failures arrive in the body of a 200 | `h35`, `h36` |
| Assumes both vendors fail alike | The annex's 5xx must not be retried, and its wait is in milliseconds, in the body | `v9`, `h34` |

**Edge cases.**

- `datetime.strptime(text, "%Y-%m-%d")` takes `2027-3-1` (`h5`), and `date.fromisoformat` takes `20270301` and `2027-W09-1`, which no case sends and the contract refuses. Each refuses `2027-02-30` (`h6`, `h10`), so the form needs a check of its own: `re.fullmatch`, since `re.match` with `$` lets a trailing newline through, and `[0-9]`, since `\d` matches digits of every script.
- `if not available` calls a day with no desks left "not on sale". Zero is a count (`h1`).
- `date=` is a missing date, not a malformed one (`h3`). `parse_qs` drops a blank value unless asked to keep it, so `.get("date", [""])` covers both.
- `urlopen` raises `HTTPError` for every status but 2xx, so the 5xx and 429 you mean to retry arrive as an exception, with the status in `code` and the body still to read. A timeout arrives as `TimeoutError`, or as `URLError` while connecting; both are `OSError`.
- A 200 does not mean a usable answer: its body may be broken (`h26`) or a valid JSON document of the wrong shape, and `body.get("rooms", [])` quietly reports a working vendor with no rooms (`h27`).
- An empty list from a vendor means "nothing on that day", which is not `unavailable` (`v4`).
- A slot of the annex needs its end worked out, and its times padded: `from_minute` 425 is `07:05`, which `divmod` and `:02d` give (`h31`).
- Validate before you call anyone. A bad date that reaches a vendor costs a request and may look like the vendor's failure (`h16`, `h29`).
- `/desks` needs no vendor, so it should not slow down or fail with one (`h30`).
- `BaseHTTPRequestHandler` answers a method it has no `do_` method for with a 501 page in HTML, so a 405 in JSON needs `do_POST` and the rest (`h11`, `h18`).
