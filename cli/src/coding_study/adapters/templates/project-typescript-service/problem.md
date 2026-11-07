# {{title}}

## Statement

TODO: the small running service to build over 2 levels, written from scratch in your own words (docs/specs/content.md#copyright-policy). `cstudy` runs it in a Docker sandbox and judges what it answers over HTTP.

## Input

TODO: the requests the service takes.

## Output

TODO: what it answers: status, headers and body. Your app reads its port from `PORT` and listens on all interfaces inside the container (`0.0.0.0`), and `/health` answers 2xx once it is ready.

## Project

TODO: what the starter holds. `src/server.ts` starts the service. `cstudy test` starts it in a sandbox and runs `node --test` beside it; the app has no network beyond its stack, and `.env` lists what it reads.

## Level 1: Answer on one endpoint

TODO: the first endpoint, and one small change, so the starter does not pass untouched.

### Example 1

TODO: a request and the response it gets.

## Level 2: Answer on a second endpoint

TODO: what the second level adds.

### Example 1

TODO: a request and the response it gets.

## Constraints

- TODO: the limits your service must hold to.

## Hints

### Hint 1

TODO: a nudge toward what to do first.

### Hint 2

TODO: a stronger nudge.
