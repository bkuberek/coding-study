# Rooms in TypeScript

## Statement

A coworking space sells desk passes, counted per day, and meeting rooms from a room vendor. Build the small service that answers for both.

## Input

HTTP requests on `/desks`, `/desks/book` and `/rooms`.

## Output

JSON. Your app reads its port from `PORT` and listens on all interfaces inside the container (`0.0.0.0`), and `/health` answers 2xx once it is ready.

## Project

`src/server.ts` starts the service. `cstudy test` starts it in a sandbox and runs its tests beside it; the app has no network beyond its stack, and `.env` lists what it reads. `scripts/seed.ts` runs first and keeps the stock in `CSTUDY_DATA_DIR`.

## Level 1: Count the desk passes

`GET /desks?date=YYYY-MM-DD` answers the day's count, and a date that is missing or not a date is a 400. `POST /desks/book` takes one pass.

### Example 1

<!-- case: v1 -->
A day's count: `GET /desks?date=2027-03-01` answers 200 with `{"date": "2027-03-01", "available": 12}`.

### Example 2

<!-- case: v2 -->
No date: `GET /desks` answers 400 with `{"error": "date is required"}`.

## Level 2: Serve the rooms

`GET /rooms` answers the vendor's rooms with `"degraded": false`. When the vendor fails, it answers no rooms with `"degraded": true`. A 429 is the exception: wait for `Retry-After`, then retry once.

### Example 1

<!-- case: v3 -->
All is well: `GET /rooms` answers 200 with the vendor's rooms.

### Example 2

<!-- case: v4 -->
The vendor is down: `GET /rooms` answers 200 with `{"rooms": [], "degraded": true}`.

## Constraints

- Give up on a vendor call after 1 second.

## Hints

### Hint 1

Read `API.md` under `vendors/room-vendor/`.

### Hint 2

`Retry-After` is in seconds.
