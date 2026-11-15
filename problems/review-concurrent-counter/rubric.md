# Review: Concurrent Counter Service: Rubric

## Finding the issues

- [ ] Flags the unsynchronized map write in `Record` and says it crashes the process, not just miscounts.
- [ ] Flags the lock held across database calls in `Flush` and connects it, with the missing timeout, to stalling every request.
- [ ] Flags the check-then-act on new tenants and the lost increments it causes.
- [ ] Flags the value receiver on `Pending` copying the mutex.
- [ ] Flags `Snapshot` returning the internal map.
- [ ] Flags billing by the client-supplied `X-Tenant-ID` header.
- [ ] Flags `/internal/usage` exposed on the public listener.
- [ ] Flags lost usage on shutdown and deploys.
- [ ] Flags double billing when a flush commits but reports failure.
- [ ] Flags the missing concurrent test under `-race`.

## Prioritization

- [ ] Leads with the crash and the stall; style issues come last and are marked as nits.
- [ ] Separates must-fix-before-merge from follow-ups explicitly.
- [ ] Gives an overall verdict (request changes) with a one-line reason.

## Actionable comments

- [ ] Every comment names its location (file and function or line).
- [ ] Proposes a concrete fix for the locking design (swap the map under the lock, I/O outside it) rather than only describing the problem.
- [ ] Suggests tooling that would have caught it (`go test -race`, `go vet` in CI).

## Tone and collaboration

- [ ] Acknowledges what the change gets right (in-process aggregation, periodic flush).
- [ ] Phrases comments about the code, not the author, and explains why each issue matters.
- [ ] Groups related line comments into one design comment instead of repeating the same point.

## Asking about intent

- [ ] Asks whether billing must be exactly-once, since that decides the flush design.
- [ ] Asks where the tenant identity should come from, or points to the authenticated context.
- [ ] Asks whether metering failures may fail customer requests.
