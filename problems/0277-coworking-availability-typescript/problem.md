# Coworking Availability (TypeScript)

## Statement

A coworking space sells two things by the day. Hot desks are a daily count the space keeps itself. Meeting rooms belong to outside vendors, who sell them in time slots and who are not always up.

Members want one answer: what can I book on this day? Build the small service that gives it, in levels, and keep it answering when a vendor fails. `cstudy` runs your app in a Docker sandbox with mock servers for the vendors, and judges it by what it answers over HTTP and by what the vendors saw it send. The space, the vendors, their paths and their numbers are invented.

## Input

HTTP requests with a `date` query parameter. `GET /desks?date=YYYY-MM-DD` comes first, and each level names what it adds.

## Output

JSON, always with `Content-Type: application/json`. Your app reads its port from `PORT` and listens on all interfaces inside the container (`0.0.0.0`), and `GET /health` answers 200 once it is ready.

## Project

`cstudy start` copies the service into `projects/coworking-availability-typescript/`, and `cstudy dev` runs it with its vendors. Node runs the files by stripping their types, so write no `enum`, no `namespace` and no constructor parameter properties, and import your own files with their `.ts` extension.

- `src/server.ts`: the routes, and where the server starts.
- `src/desks.ts`: `DeskInventory`, the daily counts, read from `data/desks.json`.
- `data/desks.json`: the seeded counts, which are the space's own data. There is no database.
- `tests/`: your tests, run by `cstudy test`, with `tests/vendorScenario.ts` to set a vendor's visible scenario from a test.
- `vendors/<name>/API.md`: each vendor's contract, for reading. Nothing depends on these copies.
- `.env`: what your app reads, written by `cstudy start` from the problem's settings. Your app's environment already holds it.

`cstudy test` starts a sandbox, runs your tests beside the app, and then the visible cases of your open levels. The app has no network beyond its stack. `cstudy submit` grades every case of the open levels, hidden ones included, and opens the next level when they all pass. Each submission grades the earlier levels again, so a later change must keep their answers. To watch a failure yourself, run `cstudy dev --scenario room-vendor=outage` and ask with `curl`.

## Level 1: Desks by day

`GET /desks?date=YYYY-MM-DD` already answers the count for a day the space sells. Read the code, then make it answer properly when the request is wrong.

| Request | Status | Body |
|---------|--------|------|
| A day on sale | 200 | `{"date": "2027-03-01", "available": 12}` |
| `date` missing or empty | 400 | `{"error": "date is required"}` |
| `date` not a real day, written `YYYY-MM-DD` | 400 | `{"error": "date must be a real day, as YYYY-MM-DD"}` |
| A real day with no entry in `data/desks.json` | 404 | `{"error": "no desks on sale for that date"}` |
| A method other than `GET` on a path this API has | 405 | `{"error": "method not allowed"}` |
| Any other path | 404 | `{"error": "not found"}` |

A day that is on sale with no desks left answers 200 with `"available": 0`: that is a count, not an error.

### Example 1

<!-- case: v1 -->

A day on sale: `GET /desks?date=2027-03-01` answers 200 with `{"date": "2027-03-01", "available": 12}`.

### Example 2

<!-- case: v2 -->

No date: `GET /desks` answers 400 with `{"error": "date is required"}`.

## Level 2: Rooms from the vendor

Add `GET /availability?date=YYYY-MM-DD`, one answer with both things a member can book. The rooms come from `room-vendor`, which your app reaches at `ROOM_VENDOR_URL` and which `vendors/room-vendor/API.md` documents.

```json
{
  "date": "2027-03-01",
  "desks": {"available": 12},
  "rooms": {
    "slots": [
      {"room": "elm", "start": "09:00", "end": "10:30", "vendor": "room-vendor"},
      {"room": "oak", "start": "09:00", "end": "10:00", "vendor": "room-vendor"},
      {"room": "oak", "start": "11:00", "end": "12:00", "vendor": "room-vendor"}
    ],
    "unavailable": []
  }
}
```

- `slots` holds only what can be booked, one entry per open slot, and names the vendor that sells it, since that is who a booking goes to.
- `slots` is sorted by `start`, then by `room`, each compared as plain text, whatever order the vendor lists them in.
- `unavailable` names the vendors that gave no usable answer. It stays empty for now.
- A wrong request gets the answers of level 1, for the same reasons. A vendor never hears about a day this API refuses, so a bad date costs it nothing.

`GET /desks` stays as it is, and needs no vendor.

### Example 1

<!-- case: v3 -->

`GET /availability?date=2027-03-01` answers 200 with the body above, after one request to the vendor.

### Example 2

<!-- case: v4 -->

The vendor has no rooms on `2027-03-02`: `GET /availability?date=2027-03-02` answers 200 with `"desks": {"available": 8}` and `"rooms": {"slots": [], "unavailable": []}`.

## Level 3: When the vendor fails

A vendor's bad minute must not become your outage. `GET /availability` now always answers 200 for a valid day: the desks are the space's own, so they are still there, and a vendor that gives no usable answer goes in `unavailable`, with no slots from it:

```json
{"date": "2027-03-01", "desks": {"available": 12}, "rooms": {"slots": [], "unavailable": ["room-vendor"]}}
```

Some failures pass, so some are worth another try. Others are not, and an impatient client makes a struggling vendor worse. The request log of the mock server shows what your app really did.

| The vendor | Your app |
|------------|----------|
| Answers 5xx | Tries again after waiting at least 200 ms, up to 3 requests in all |
| Answers 429 with `Retry-After: <seconds>` | Tries again after waiting at least that long, counted in the same 3 requests |
| Answers 429 with no `Retry-After` | Tries again after waiting at least 200 ms, counted in the same 3 |
| Answers another 4xx | Does not try again: asking again will not change it |
| Takes more than 1.5 s to answer | Gives up on that request and does not try again: it is already struggling, and your caller is waiting |
| Answers 2xx with a body that is not what the API documents | Does not try again |

The wait counts from the moment the vendor's answer arrived. If the last of the 3 requests fails too, the vendor is `unavailable`.

### Example 1

<!-- case: v5 -->

The vendor answers 500 to everything: `GET /availability?date=2027-03-01` answers 200 with the desks and `"rooms": {"slots": [], "unavailable": ["room-vendor"]}`, after exactly 3 requests to the vendor, at least 200 ms apart.

### Example 2

<!-- case: v6 -->

The vendor answers 429 with `Retry-After: 1` to everything: the same answer, after 3 requests at least a second apart.

### Example 3

<!-- case: v7 -->

The vendor takes 3 s to answer: the same answer, after 1 request.

## Level 4: A second vendor

The space has taken over the building next door, whose rooms are sold by a different vendor. `annex-vendor`, at `ANNEX_VENDOR_URL`, is documented in `vendors/annex-vendor/API.md`, and it has little in common with the first one: other paths, another form of date, times as minutes, and its own ways of failing.

`GET /availability` now answers for both, in the same shape. An annex slot looks like any other, with `"vendor": "annex-vendor"`, and the two are sorted together. One vendor's failure touches nothing of the other's: its slots are still there, and only the vendor that failed goes in `unavailable`, sorted by name.

| `annex-vendor` | Your app |
|----------------|----------|
| Answers `{"ok": false, "error": {"code": "BUSY", "retry_after_ms": <ms>}}` with a 200 | Tries again after waiting at least that long, up to 2 requests in all |
| Answers `"ok": false` with any other code | Does not try again |
| Answers 5xx | Does not try again: its documentation says a 5xx means it is down for maintenance |
| Takes more than 1.5 s to answer | Gives up on that request and does not try again |
| Answers with a body that is not what the API documents | Does not try again |

The rules of level 3 still hold for `room-vendor`, and every earlier level is graded again, so a day with nothing from the annex must answer as it did.

### Example 1

<!-- case: v8 -->

Both vendors have rooms on `2027-03-08`: `GET /availability?date=2027-03-08` answers 200 with `"unavailable": []` and these slots, after one request to each vendor:

```json
[
  {"room": "A1", "start": "08:00", "end": "08:45", "vendor": "annex-vendor"},
  {"room": "A2", "start": "09:00", "end": "10:00", "vendor": "annex-vendor"},
  {"room": "oak", "start": "09:00", "end": "10:00", "vendor": "room-vendor"},
  {"room": "A1", "start": "09:30", "end": "11:00", "vendor": "annex-vendor"},
  {"room": "elm", "start": "13:00", "end": "14:00", "vendor": "room-vendor"}
]
```

### Example 2

<!-- case: v9 -->

The annex is down for maintenance on the same day: the answer holds the two `room-vendor` slots and `"unavailable": ["annex-vendor"]`, after one request to the annex.

## Constraints

- A valid day always answers 200 from level 3 on, whatever the vendors do.
- At most 3 requests to `room-vendor` and 2 to `annex-vendor` for one request to your API.
- A wait never comes up short: the hidden cases measure the gap between a vendor's answer and your next request.
- Your app reaches the vendors only through `ROOM_VENDOR_URL` and `ANNEX_VENDOR_URL`, and listens on all interfaces inside the container.

## Follow-ups

- A 429 says to wait 30 s and your caller will not wait that long. What should your API answer, and should its next request ask the vendor at all?
- Every request to your API asks every vendor. Which of them could be cached, for how long, and what does a member see when a cached slot has just gone?
- `room-vendor` has been failing for ten minutes. What would a circuit breaker change here, and what would it cost in the minute after the vendor recovers?
- A third vendor is coming. Which files would you touch, and which would you hope not to?

## Hints

### Hint 1

Keep the date rules in one function used by both endpoints, and call it before anything else happens. Check what your language's date parser does with `2027-02-30` before you trust it.

### Hint 2

Flatten first, sort last. The vendor's nesting by room is its own business, and your answer's order should not depend on it.

### Hint 3

Decide what to do from the vendor's answer in one pure function: how long to wait before trying again, or not to try again. The loop around it then only counts and waits.

### Hint 4

Give each vendor its own client with the same small interface, a method that takes a date and returns slots or fails. Then the code that merges them knows nothing about shapes or retries, and one that fails cannot take another with it.
