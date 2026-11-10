# Coworking Availability (Java): Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | per request | per request | default answer: one client per vendor, each hiding its own shape and failures behind the same small interface |

## How the project grows level by level

| Level | New requirement | What the code adds |
|-------|-----------------|--------------------|
| 1 | The right answer to a wrong request | `Days.parse`; `CoworkingApi`, with a map of routes and `Refused`, thrown before anything else happens; `Server` only moves HTTP in and out |
| 2 | One answer with the vendor's slots | `vendors.RoomVendor`, with the vendor's answer as records, and `RoomAvailability`, which flattens and sorts |
| 3 | A vendor that fails | `VendorHttp.get`, `VendorUnavailableException`, `Retries.ask`, and the room vendor's `waitBeforeRetry`; the exception becomes a name in `unavailable` |
| 4 | A second vendor | `vendors.AnnexVendor`, the `RoomSource` interface, and a virtual thread per vendor in the merge |

## Approach: reference (One client per vendor behind one shape of answer)

### Intuition

The service has two very different kinds of data, and the design should let you see that. The desks are the space's own: they are always there, so nothing about a vendor can ever change what they answer. The rooms are someone else's: every call may fail, and the only honest question is what your caller sees when it does.

So a failure is part of the answer, not an accident. A vendor that gives no usable answer goes in `unavailable`, and the caller gets a true answer about the rest, which is what "degrade" means. The request fails only when the request is wrong.

Retries are a load decision before they are an error-handling one. A 5xx often passes, so asking again is worth a little. A 429 is the vendor telling you the number, so you stop guessing and wait that long. A slow vendor is already struggling, and your caller is waiting, so you do not ask it again. Each vendor has its own answer to all of this, which is why its rules belong in that vendor's class, while the loop that applies them can be shared.

### Say it out loud

"Desks come from our own data, so I answer them no matter what. Rooms come from vendors, and I treat each vendor as something that can fail on any request, so its failure goes in the answer rather than becoming a 500 from me.

"Every way a vendor can fail ends as one checked exception of mine, `VendorUnavailableException`: no answer in time, a status that will not change, a body that is not JSON or not the documented shape. The compiler makes each client say so, and the merge catches exactly that and nothing else, so a bug in my own code still shows up as a bug.

"I read a vendor's body into records of what its API documents. Each record's compact constructor refuses a part that is missing, so Jackson's failure to build one is a broken answer, and I never pass on an empty list where the vendor sent nonsense.

"For retries, I separate what is worth retrying from how long to wait. Each vendor has a pure function that reads an answer and returns the wait, or an empty `Optional` for not asking again. One small loop does the counting and the sleeping for both. I don't retry a timeout, and I bound the total.

"I ask both vendors at once, each on a virtual thread, because their waits should not add up. Closing the executor waits for both, and each `Future` then holds either the slots or the exception, so one vendor failing can't take the other with it."

### Algorithm

1. Refuse a wrong request first: no date, not a real day, a day not on sale. `Refused` carries the reply, and nothing has reached a vendor yet.
2. Submit one task per vendor to `Executors.newVirtualThreadPerTaskExecutor()`, and close it, which waits for every task.
3. In a client, send the request with a limit of 1.5 s. While its rules say an answer is worth retrying, sleep as long as they say and ask again, up to that vendor's limit.
4. Read the body into the vendor's records, and turn the open slots into `Slot`s. A body Jackson cannot build them from throws `VendorUnavailableException`.
5. A `Future` that succeeded gives slots, and one that failed with `VendorUnavailableException` gives a name in `unavailable`. Sort both, and answer with the desks.

### Design

- `Server.java`: `main`, and the handler, which only moves HTTP in and out and turns an exception of the API's into a 500, so a test or another server could drive the API without it.
- `CoworkingApi.java`: every answer from a method and a target, with the routes as a map, so a known path with the wrong method answers 405 in one place; `Refused`, a checked exception with the reply in it, and the date rules both endpoints share.
- `Reply.java`: a status and a body for Jackson to write.
- `Days.java`: `parse`, a pattern for the form and then `LocalDate.parse` for the day.
- `DeskInventory.java` and `Query.java`: unchanged from the starter.
- `RoomAvailability.java`: the merge, a record that is also the `rooms` of the answer, which knows only `RoomSource` and `VendorUnavailableException`.
- `vendors/`: the seam. `Slot`, `RoomSource` and `VendorUnavailableException` are public; `VendorHttp` (the request limit and the answer), `Retries` (the loop) and each vendor's records stay inside the package.
- `vendors/RoomVendor.java`: the first vendor's path, shape and retry rules, with `waitBeforeRetry` a pure function that a test calls.
- `vendors/AnnexVendor.java`: the second vendor's day form, minutes and failures in the body.

Not graded, and worth discussing:

- **A circuit breaker.** After a run of failures, skip the vendor for a while and answer `unavailable` at once, so that a long outage costs neither the vendor's capacity nor your caller's time.
- **Caching.** Slots change slowly enough that a few seconds of cache would shield the vendor from a burst, at the price of offering a slot that has just gone. A booking must still ask the vendor.
- **A budget for the whole request.** With 3 tries and a `Retry-After`, one request can wait for seconds. A real service would give each request a deadline and stop waiting for a vendor once it would be missed.
- **A third vendor.** It means one new class and one line in `main`, which is the point of the seam.
- **Structured concurrency.** `StructuredTaskScope` says "these tasks belong to this request" better than an executor does, and cancels them together; it is a preview in JDK 25, so the reference keeps to the executor.

### Correctness

A valid day always answers 200: the desks come from local data, and every way a vendor can fail ends as a `VendorUnavailableException` inside its client, which the merge turns into a name in `unavailable`. Every slot comes through a record whose constructor checked it against its vendor's contract, so a broken answer never shows as an empty list. Nothing is sent for a refused date, since `onSale` runs before any client. Each client counts its own requests through `Retries.ask`, so the limits hold whatever mix of failures comes.

### Complexity

- Time: per request — one to three requests to each vendor, at the same time, then a sort of the slots
- Space: per request — the vendors' answers while they are merged

### Trade-offs

Asking both vendors at once keeps one vendor's waits from adding to the other's, at the cost of always spending both vendors' capacity. A virtual thread costs next to nothing, so a thread per vendor per request is the plain way to do it, and blocking calls and `Thread.sleep` read as they run. The retry loop is shared and the rules are not: `Retries.ask` only counts and sleeps, and each vendor's `waitBeforeRetry` reads its own kind of answer, a status and a header for one, a body for the other.

Records with checks in their constructors read a body and validate it in one step, and say in the code what the vendor promised. The cost is a record per level of the body, and fields the vendor adds later are ignored, which is what you want from a client.

`HttpRequest.timeout` limits the wait for the answer, and the mock vendors are slow before their first byte, so 1.5 s holds. A vendor that answered at once and then sent its body a byte at a time would need a deadline of your own around the whole call.

`com.sun.net.httpserver` and `java.net.http` keep the dependencies at Jackson and JUnit, and the seam visible. A framework would route and serialize for you, added to the build and the lock; the date rules, the retry rules and the merge would not change.

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
| Lets a vendor's exception reach the route | A vendor's bad minute becomes a 500 for a member who wanted a desk | `v5` |
| Calls `get()` on each future in one `try`, or asks the vendors one after the other | The first to fail ends the merge, so one vendor takes the other down | `h32`, `v9` |
| Treats a non-2xx as the only failure on the annex | Its failures arrive in the body of a 200 | `h35`, `h36` |
| Assumes both vendors fail alike | The annex's 5xx must not be retried, and its wait is in milliseconds, in the body | `v9`, `h34` |

**Edge cases.**

- `LocalDate.parse` refuses `2027-02-30` (`h6`, `h10`) and `2027-3-1` (`h5`), but takes `+12027-03-01`, which the contract refuses, so the form needs a check of its own. `Matcher.matches` matches the whole text, a trailing newline included, and `[0-9]` keeps to ASCII digits. A `DateTimeFormatter.ofPattern("yyyy-MM-dd")` resolves leniently by default, `SMART`, and turns `2027-02-30` into the last day of February.
- `desks.availableOn(day)` is an `OptionalInt`, not an `int` with 0 for "not on sale". Zero is a count (`h1`).
- `date=` is a missing date, not a malformed one (`h3`): `Query.value` gives `""` for both.
- `HttpClient.send` returns every status as a response, so the 5xx and 429 you mean to retry come back as values. A timeout throws `HttpTimeoutException`, and a refused connection `ConnectException`; both are `IOException`s.
- A 200 does not mean a usable answer: its body may be broken (`h26`) or valid JSON of the wrong shape, and reading `rooms` with a default of an empty list quietly reports a working vendor with no rooms (`h27`).
- An empty list from a vendor means "nothing on that day", which is not `unavailable` (`v4`).
- A slot of the annex needs its end worked out, and its times padded: `from_minute` 425 is `07:05`, which `"%02d:%02d"` gives (`h31`).
- Validate before you call anyone. A bad date that reaches a vendor costs a request and may look like the vendor's failure (`h16`, `h29`).
- `/desks` needs no vendor, so it should not slow down or fail with one (`h30`).
- `HttpServer` hands every method to the same handler, so a 405 is yours to answer, in JSON (`h11`, `h18`).
- The JDK's `HttpClient` asks to upgrade a plain connection to HTTP/2 unless told otherwise; the clients pin HTTP/1.1, which every vendor here speaks.
