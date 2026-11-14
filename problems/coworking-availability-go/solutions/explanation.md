# Coworking Availability (Go): Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | per request | per request | default answer: one client per vendor, each hiding its own shape and failures behind the same small interface |

## How the project grows level by level

| Level | New requirement | What the code adds |
|-------|-----------------|--------------------|
| 1 | The right answer to a wrong request | `parseDay`; `newServer` with a map of routes, and `dayOnSale`, which refuses a wrong request before anything else happens; `write` only moves a `reply` out |
| 2 | One answer with the vendor's slots | `rooms.RoomVendor`, with the vendor's body as structs, and `askEveryVendor`, which flattens and sorts |
| 3 | A vendor that fails | `get`, with its deadline, `ask`, the loop, and `roomVendorWaitBeforeRetry`; an error becomes a name in `unavailable` |
| 4 | A second vendor | `rooms.AnnexVendor`, the `rooms.Source` interface, and a goroutine per vendor in the merge |

## Approach: reference (One client per vendor behind one shape of answer)

### Intuition

The service has two very different kinds of data, and the design should let you see that. The desks are the space's own: they are always there, so nothing about a vendor can ever change what they answer. The rooms are someone else's: every call may fail, and the only honest question is what your caller sees when it does.

So a failure is part of the answer, not an accident. A vendor that gives no usable answer goes in `unavailable`, and the caller gets a true answer about the rest, which is what "degrade" means. The request fails only when the request is wrong.

Retries are a load decision before they are an error-handling one. A 5xx often passes, so asking again is worth a little. A 429 is the vendor telling you the number, so you stop guessing and wait that long. A slow vendor is already struggling, and your caller is waiting, so you do not ask it again. Each vendor has its own answer to all of this, which is why its rules belong with that vendor's type, while the loop that applies them can be shared.

### Say it out loud

"Desks come from our own data, so I answer them no matter what. Rooms come from vendors, and I treat each vendor as something that can fail on any request, so its failure goes in the answer rather than becoming a 500 from me.

"Every way a vendor can fail ends as an `error` from its `OpenSlots`: no answer in time, a status that will not change, a body that is not JSON or not the documented shape. The merge needs nothing more than that: an error is a name in `unavailable`, and slots are slots.

"I decode a vendor's body into structs of what its API documents, and then check what `encoding/json` would let pass: it ignores a field it does not know and leaves one that is missing at its zero value. A list that is left out decodes as `nil`, unlike an empty one, so `nil` means the vendor broke its contract, and I never pass on an empty list where it sent nonsense.

"For retries, I separate what is worth retrying from how long to wait. Each vendor has a pure function that reads an answer and returns the wait, or `false` for not asking again. One small generic loop, `ask`, does the counting and the waiting for both, and its wait ends early when the caller gives up. I don't retry a timeout, and I bound the total.

"I ask both vendors at once, a goroutine each, because their waits should not add up. Each writes its answer into its own index of a slice, so they share nothing, and `WaitGroup.Wait` hands me both. The request's context flows down to every call, and each call has its own 1.5 s deadline from `context.WithTimeout`, over the whole exchange, the body included."

### Algorithm

1. Refuse a wrong request first: no date, not a real day, a day not on sale. `dayOnSale` gives the reply that refuses it, and nothing has reached a vendor yet.
2. Start one goroutine per vendor with `sync.WaitGroup.Go`, and wait for them all.
3. In a client, send the request with a deadline of 1.5 s. While its rules say an answer is worth retrying, wait as long as they say and ask again, up to that vendor's limit.
4. Decode the body into the vendor's structs, check what they promise, and turn the open slots into `rooms.Slot`s. A body that cannot be decoded, or lacks a part, is an error.
5. Slots from every vendor that answered, and the names of those that did not; sort both, and answer with the desks.

### Design

- `main.go`: `main`, and `vendorsAt`, the one list of vendors, which the tests use too.
- `server.go`: every answer from a path and a method, with the routes as a map, so a known path with the wrong method answers 405 in one place and an unknown one 404, both in JSON; `dayOnSale`, the date rules both endpoints share; `reply`, a status and a body for `encoding/json`.
- `days.go`: `parseDay`, a pattern for the form and then `time.Parse` for the day.
- `availability.go`: the merge, which knows only `rooms.Source` and `error`.
- `desks.go`: unchanged from the starter.
- `internal/rooms/`: the seam. `Slot`, `Source`, `RoomVendor` and `AnnexVendor` are exported; `get` (the deadline and the whole answer), `ask` (the loop) and each vendor's structs stay inside the package, and `internal/` keeps the package to this module.
- `internal/rooms/roomvendor.go`: the first vendor's path, shape and retry rules, with `roomVendorWaitBeforeRetry` a pure function that a test calls.
- `internal/rooms/annexvendor.go`: the second vendor's day form, minutes and failures in the body.

Not graded, and worth discussing:

- **A circuit breaker.** After a run of failures, skip the vendor for a while and answer `unavailable` at once, so that a long outage costs neither the vendor's capacity nor your caller's time.
- **Caching.** Slots change slowly enough that a few seconds of cache would shield the vendor from a burst, at the price of offering a slot that has just gone. A booking must still ask the vendor.
- **A budget for the whole request.** With 3 tries and a `Retry-After`, one request can wait for seconds. The request's context already reaches every wait; a deadline on it, `context.WithTimeout(r.Context(), …)` in the handler, would stop waiting for a vendor once the caller's budget is spent.
- **A third vendor.** It means one new type in `internal/rooms` and one line in `vendorsAt`, which is the point of the seam.
- **errgroup.** `golang.org/x/sync/errgroup` runs goroutines and cancels the rest at the first error, which is the opposite of what the merge wants: one vendor failing must not stop the other. A `WaitGroup` and a slot per vendor say that plainly, with no module to add.

### Correctness

A valid day always answers 200: the desks come from local data, and every way a vendor can fail ends as an error from its `OpenSlots`, which the merge turns into a name in `unavailable`. Every slot comes through a check of its vendor's contract, so a broken answer never shows as an empty list. Nothing is sent for a refused date, since `dayOnSale` runs before any client. Each client counts its own requests through `ask`, so the limits hold whatever mix of failures comes. The goroutines write to separate elements of a slice and are read only after `Wait`, so there is no data race.

### Complexity

- Time: per request — one to three requests to each vendor, at the same time, then a sort of the slots
- Space: per request — the vendors' answers while they are merged

### Trade-offs

Asking both vendors at once keeps one vendor's waits from adding to the other's, at the cost of always spending both vendors' capacity. A goroutine costs a few KiB, so one per vendor per request is the plain way to do it, and a blocking call and a wait read as they run. The retry loop is shared and the rules are not: `ask` only counts and waits, and each vendor's wait function reads its own kind of answer, a status and a header for one, a body for the other.

Structs with a check after decoding say in the code what the vendor promised. The cost is a check per part, which `encoding/json` will not do for you, and fields the vendor adds later are ignored, which is what you want from a client.

`net/http` and `encoding/json` keep the module at no dependency at all, and `go.sum` empty. A router or a validation library would be a module to add and lock; the date rules, the retry rules and the merge would not change.

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
| `http.Get` with the default client | `http.DefaultClient` has no timeout, so a slow vendor holds the request as long as it likes | `v7`, `h37` |
| Asks the vendors one after the other, or returns at the first error | The waits add up, or one vendor takes the other down | `h32`, `v9` |
| Treats a non-2xx as the only failure on the annex | Its failures arrive in the body of a 200 | `h35`, `h36` |
| Assumes both vendors fail alike | The annex's 5xx must not be retried, and its wait is in milliseconds, in the body | `v9`, `h34` |

**Edge cases.**

- `time.Parse(time.DateOnly, …)` refuses `2027-02-30` (`h6`, `h10`) and `2027-3-1` (`h5`), but takes a signed year, `-027-03-01`, which the contract refuses, so the form needs a check of its own. In Go's regular expressions `$` is the end of the text, with no newline allowed before it, and `[0-9]`, like `\d`, keeps to ASCII digits; `time.Parse` itself never rounds a day that does not exist into one that does.
- `availableOn` answers a count and whether the day is on sale, not 0 for "not on sale". Zero is a count (`h1`).
- `date=` is a missing date, not a malformed one (`h3`): `URL.Query().Get` gives `""` for both.
- A `nil` slice is written as `null` by `encoding/json`, and an empty one as `[]`. `slots` and `unavailable` start as empty slices, so a day with no rooms answers `[]` (`v4`, `h33`).
- `encoding/json` ignores a field it does not know and leaves a missing one at its zero value, so `{"status": "ok"}` decodes into the room vendor's struct with no error. Reading `rooms` with no check quietly reports a working vendor with no rooms (`h27`, and `h39` for the annex).
- `client.Do` returns every status as a response, so the 5xx and 429 you mean to retry come back as values. A deadline that passes is an error, and so is a refused connection.
- A 200 does not mean a usable answer: its body may be broken (`h26`, `h38`).
- An empty list from a vendor means "nothing on that day", which is not `unavailable` (`v4`).
- A slot of the annex needs its end worked out, and its times padded: `from_minute` 425 is `07:05`, which `"%02d:%02d"` gives (`h31`).
- Validate before you call anyone. A bad date that reaches a vendor costs a request and may look like the vendor's failure (`h16`, `h29`, `h41`).
- `/desks` needs no vendor, so it should not slow down or fail with one (`h30`).
- `http.ServeMux` with a pattern such as `GET /desks` answers another method with its own 405 in plain text, not JSON, and redirects a path it can clean, such as `/desks/../desks`; a map of routes and one handler answer both as this API does (`h11`, `h18`).
- A panic in a goroutine you started ends the whole server: `net/http` recovers only the handler's own goroutine. The vendors' clients return errors and never panic on a vendor's body.
- Close every response body, or read it to the end, so the connection can be used again; `get` reads it whole within its deadline and closes it.
