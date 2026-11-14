# Coworking Availability (Kotlin): Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | per request | per request | default answer: one client per vendor, each hiding its own shape and failures behind the same small interface |

## How the project grows level by level

| Level | New requirement | What the code adds |
|-------|-----------------|--------------------|
| 1 | The right answer to a wrong request | `parseDay`; `CoworkingApi`, with an enum of routes and a sealed `OnSale`, decided before anything else happens; `Main.kt` only moves HTTP in and out |
| 2 | One answer with the vendor's slots | `vendors.RoomVendor`, with the vendor's answer as `@Serializable` classes, and `roomAvailability`, which flattens and sorts |
| 3 | A vendor that fails | `fetch`, `VendorUnavailable`, `askWithRetries` with `delay`, and the room vendor's `waitBeforeRetry`; the exception becomes a name in `unavailable` |
| 4 | A second vendor | `vendors.AnnexVendor`, the `RoomSource` interface, and an `async` per vendor in one `coroutineScope` |

## Approach: reference (One client per vendor behind one shape of answer)

### Intuition

The service has two very different kinds of data, and the design should let you see that. The desks are the space's own: they are always there, so nothing about a vendor can ever change what they answer. The rooms are someone else's: every call may fail, and the only honest question is what your caller sees when it does.

So a failure is part of the answer, not an accident. A vendor that gives no usable answer goes in `unavailable`, and the caller gets a true answer about the rest, which is what "degrade" means. The request fails only when the request is wrong.

Retries are a load decision before they are an error-handling one. A 5xx often passes, so asking again is worth a little. A 429 is the vendor telling you the number, so you stop guessing and wait that long. A slow vendor is already struggling, and your caller is waiting, so you do not ask it again. Each vendor has its own answer to all of this, which is why its rules belong in that vendor's class, while the loop that applies them can be shared.

### Say it out loud

"Desks come from our own data, so I answer them no matter what. Rooms come from vendors, and I treat each vendor as something that can fail on any request, so its failure goes in the answer rather than becoming a 500 from me.

"A wrong request is not an exception here, it is one of two things `onSale` returns, a day or a refusal, and the compiler makes every route handle both. A vendor's failure is different: it happens deep in a client, so it is one exception of mine, `VendorUnavailable`, which each client throws for no answer in time, a status that will not change, or a body that is not the documented shape.

"I decode a vendor's body into `@Serializable` classes of what its API documents, with unknown keys ignored. A missing field, a wrong type or broken JSON is a `SerializationException`, which the client turns into `VendorUnavailable`, so I never pass on an empty list where the vendor sent nonsense.

"For retries, I separate what is worth retrying from how long to wait. Each vendor has a pure function that reads an answer and returns a `Duration`, or null for not asking again. One small loop does the counting and the `delay` for both. I don't retry a timeout, and I bound the total.

"I ask both vendors at once, an `async` each in one `coroutineScope`. Each `async` catches `VendorUnavailable` and returns what happened as a value, so one vendor failing can't cancel the other, while a bug in my own code still cancels everything and shows as a 500."

### Algorithm

1. Refuse a wrong request first: no date, not a real day, a day not on sale. `OnSale.Refused` carries the reply, and nothing has reached a vendor yet.
2. Start one `async` per vendor in a `coroutineScope`, and `awaitAll`.
3. In a client, send the request with `sendAsync(...).await()` and a limit of 1.5 s. While its rules say an answer is worth retrying, `delay` as long as they say and ask again, up to that vendor's limit.
4. Decode the body into the vendor's classes, and turn the open slots into `Slot`s. A body that does not decode throws `VendorUnavailable`.
5. Each vendor's answer is `Slots` or `Unavailable`. Sort the slots by start then room, and the names, and answer with the desks.

### Design

- `Main.kt`: `main`, and the handler, which only moves HTTP in and out: a request runs on a virtual thread of its own, enters coroutines with `runBlocking`, and turns an exception into a 500.
- `CoworkingApi.kt`: every answer from a method and a target, with the routes as an enum, so a known path with the wrong method answers 405 in one place and a `when` over the routes is exhaustive; the sealed `OnSale`, and the date rules both endpoints share.
- `Reply.kt`: a status and a JSON body, and `reply`, which encodes any `@Serializable` value.
- `Days.kt`: `parseDay`, a `Regex` for the form and then `LocalDate.parse` for the day, null for neither.
- `DeskInventory.kt` and `Query.kt`: unchanged from the starter.
- `RoomAvailability.kt`: the merge, which knows only `RoomSource` and `VendorUnavailable`, and the `rooms` of the answer.
- `vendors/RoomSource.kt`: the seam: `Slot`, `VendorUnavailable` and the `RoomSource` interface.
- `vendors/VendorHttp.kt`: what stays inside the package: the request limit, `Answer` and `fetch`, and `askWithRetries`.
- `vendors/RoomVendor.kt`: the first vendor's path, shape and retry rules, with `waitBeforeRetry` a pure function that a test calls.
- `vendors/AnnexVendor.kt`: the second vendor's day form, minutes and failures in the body.

Not graded, and worth discussing:

- **A circuit breaker.** After a run of failures, skip the vendor for a while and answer `unavailable` at once, so that a long outage costs neither the vendor's capacity nor your caller's time.
- **Caching.** Slots change slowly enough that a few seconds of cache would shield the vendor from a burst, at the price of offering a slot that has just gone. A booking must still ask the vendor.
- **A budget for the whole request.** With 3 tries and a `Retry-After`, one request can wait for seconds. `withTimeoutOrNull` around the merge, or around each vendor, gives the request a deadline in one line, which is one reason to reach for coroutines here.
- **A third vendor.** It means one new class and one line in `main`, which is the point of the seam.
- **A server framework.** Ktor would route and serialize for you, with suspending handlers and no `runBlocking`, added to the build and the lock; the date rules, the retry rules and the merge would not change.

### Correctness

A valid day always answers 200: the desks come from local data, and every way a vendor can fail ends as a `VendorUnavailable` inside its client, which the merge turns into a name in `unavailable`. Every slot comes through classes decoded against its vendor's contract, so a broken answer never shows as an empty list. Nothing is sent for a refused date, since `onSale` runs before any client. Each client counts its own requests through `askWithRetries`, so the limits hold whatever mix of failures comes.

### Complexity

- Time: per request — one to three requests to each vendor, at the same time, then a sort of the slots
- Space: per request — the vendors' answers while they are merged

### Trade-offs

Asking both vendors at once keeps one vendor's waits from adding to the other's, at the cost of always spending both vendors' capacity. Coroutines make that cheap: `fetch` suspends on the JDK client's future, and `delay` suspends instead of sleeping, so both vendors run on the request's own thread. The retry loop is shared and the rules are not: `askWithRetries` only counts and waits, and each vendor's `waitBeforeRetry` reads its own kind of answer, a status and a header for one, a body for the other.

Catching inside each `async` is the point of the merge. In a `coroutineScope`, an exception that leaves one child cancels the scope and its other children, which is right for a bug and wrong for a vendor that is down; `supervisorScope` would keep the siblings, but would still need each failure turned into a name, which the sealed `VendorAnswer` does in one place.

`@Serializable` classes read a body and check it in one step, and say in the code what the vendor promised; an `init` block holds a rule a type cannot, such as an open slot having its times. Fields the vendor adds later are ignored, which is what you want from a client.

The JDK's `HttpServer` has blocking handlers, so the handler bridges into coroutines with `runBlocking` on its virtual thread. That is the one place it belongs: at the edge, once per request.

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
| Lets `VendorUnavailable` escape an `async`, or asks the vendors one after the other | The first to fail cancels or ends the merge, so one vendor takes the other down | `h32`, `v9` |
| Treats a non-2xx as the only failure on the annex | Its failures arrive in the body of a 200 | `h35`, `h36` |
| Assumes both vendors fail alike | The annex's 5xx must not be retried, and its wait is in milliseconds, in the body | `v9`, `h34` |

**Edge cases.**

- `LocalDate.parse` refuses `2027-02-30` (`h6`, `h10`) and `2027-3-1` (`h5`), but takes `+12027-03-01`, which the contract refuses, so the form needs a check of its own. `Regex.matches` matches the whole text, a trailing newline included, and `[0-9]` keeps to ASCII digits. A `DateTimeFormatter.ofPattern("yyyy-MM-dd")` resolves leniently by default, `SMART`, and turns `2027-02-30` into the last day of February.
- `desks.availableOn(day)` is an `Int?`, not an `Int` with 0 for "not on sale". Zero is a count (`h1`).
- `date=` is a missing date, not a malformed one (`h3`): `queryValue` gives `""` for both.
- `HttpClient` returns every status as a response, so the 5xx and 429 you mean to retry come back as values. A timeout fails the future with `HttpTimeoutException`, and a refused connection with `ConnectException`; `await` rethrows both, and both are `IOException`s.
- A 200 does not mean a usable answer: its body may be broken (`h26`) or valid JSON of the wrong shape, and a field with a default of an empty list quietly reports a working vendor with no rooms (`h27`). The classes give `rooms` and `spaces` no default.
- `SerializationException` is an `IllegalArgumentException`, and so is what `require` throws in an `init` block, so the client catches the latter and covers both.
- An empty list from a vendor means "nothing on that day", which is not `unavailable` (`v4`).
- A slot of the annex needs its end worked out, and its times padded: `from_minute` 425 is `07:05`, which `"%02d:%02d"` gives (`h31`).
- Validate before you call anyone. A bad date that reaches a vendor costs a request and may look like the vendor's failure (`h16`, `h29`).
- `/desks` needs no vendor, so it should not slow down or fail with one (`h30`).
- `HttpServer` hands every method to the same handler, so a 405 is yours to answer, in JSON (`h11`, `h18`).
- The JDK's `HttpClient` asks to upgrade a plain connection to HTTP/2 unless told otherwise; the client pins HTTP/1.1, which every vendor here speaks.
