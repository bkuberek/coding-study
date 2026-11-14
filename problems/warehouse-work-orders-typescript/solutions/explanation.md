# Warehouse Work Orders (TypeScript): Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | O(n + p) per report or list request; O(p) per other request | O(n + p + k) | default answer; each level adds a folder or one narrow change to a feature |

Here `n` is the number of work orders, `p` the number of part lines and `k` the number of idempotency keys in use.

## How the project grows level by level

| Level | New requirement | What the code adds |
|-------|-----------------|--------------------|
| 1 | Retries create one order | `src/idempotency/replayCache.ts`, and a few lines in the `POST` handler |
| 2 | Partial updates | `parseChanges` in `validate.ts`, `update` in the store, and the `PATCH` route |
| 3 | Parts and cost | `src/parts/`: a store, a route file and `cost.ts`, which does the arithmetic |
| 4 | Soft delete | A private row around each order in the store, so the rest of the code never sees the mark |
| 5 | Optimistic locking | `src/shared/preconditions.ts`, and one call in each of three routes |
| 6 | The report | `src/reports/routes.ts`, which owns no data and reuses `orderCost` |

## Approach: reference (Feature folders with a frozen replay cache and costs computed on read)

### Intuition

Each level has one idea, and each idea is a promise the service makes to a client that can't see inside it.

- Level 1: "If you are not sure I heard you, ask again. You'll get the same answer."
- Level 2: "I change what you named, and nothing else."
- Level 3: "This cost is always true, because I work it out when you ask."
- Level 4: "It's gone for you, and on record for us."
- Level 5: "I'll tell you if what you read is out of date, rather than let you overwrite someone."
- Level 6: "The summary equals the sum of the parts."

All of them are about state changing while someone isn't looking, which is what makes backend work different from a function that gets its inputs and returns.

### Algorithm

1. Level 1: read the header. Parse the body first, since a body that isn't JSON can't be compared. Look the key up: same canonical JSON replays the frozen answer, different JSON is a 422, and a new key validates and creates, and only a success is remembered.
2. Level 2: for each field, ask `field in input` before you look at its value. Validate everything first, then apply, so a refusal changes nothing. Raise `version` only if a value differs.
3. Level 3: multiply every factor first, then divide once, rounding half up in whole-number arithmetic.
4. Level 4: put the mark in the store, and make `list` and `get` filter on it, so no caller can forget. Compare `includeDeleted` with `"true"`, never test it for truth.
5. Level 5: after the 404, compare `If-Match` as a number with the order's `version`, before reading the body.
6. Level 6: start from the sites and find each site's live orders. Add the per-order costs that `orderCost` returns, never the raw minutes.

### Design

| File | Responsible for |
|------|-----------------|
| `src/server.ts` | `WorkOrderApi`: builds every feature, holds the route table and the one `try`/`catch` |
| `src/shared/routing.ts`, `json.ts`, `body.ts` | How a request reaches a handler: know nothing about work orders. Unchanged from the starter |
| `src/shared/problems.ts` | Each failure the API answers on purpose |
| `src/shared/preconditions.ts` | The `If-Match` check, shared by three routes |
| `src/sites/` | The directory of sites and `GET /sites`. Unchanged from the starter |
| `src/workorders/` | The order: its model, store (with the deleted mark), validation and routes |
| `src/idempotency/replayCache.ts` | Which key got which answer |
| `src/parts/store.ts`, `routes.ts` | Part lines, and the routes that read and add them |
| `src/parts/cost.ts` | All the money arithmetic, pure, in one file |
| `src/reports/routes.ts` | Reads the other features, owns nothing, and nothing depends on it |
| `tests/cost.test.ts` | The rounding rules, tested without a request |

**Why feature folders, and what they cost.** Everything about parts is in one folder, so you can read or delete the feature at once, which layered folders don't give you. The cost is at the seams: `reports/` and `parts/` import from `workorders/`, and that direction has to stay one way, or two features end up depending on each other. In a layered service (`routes/`, `data/`), you find all the data access in one place, and every feature is spread across every folder. Neither is simply right. Being able to read both is the skill.

**Why the replay cache stores a copy.** The answer is frozen with `structuredClone` when it is remembered. Storing the `order` object itself looks the same until someone edits the order, and then a retry tells the client something the first request never said.

**Why the deleted mark lives inside the store.** If `deleted` were a field on `WorkOrder` that callers filter on, every read, today's and next year's, would have to remember it. Keeping it in a private row means forgetting isn't possible, and `GET /work-orders/:id` needs no change at all. In SQL the same idea is a view or a default scope.

**What a senior engineer says out loud.**

- Level 1: "The client generates the key, because only the client knows two requests are one attempt. I fingerprint the request, so a reused key is a visible bug instead of a silent wrong answer."
- Level 2: "`null` and missing are different requests, and JavaScript makes them very easy to mix up. So I ask `in` for presence, and only then look at the value."
- Level 3: "Money stays in whole cents, and I multiply before I divide. `19.99 * 100` isn't 1999, and `11 / 60 * 5130` isn't 940.5. I also write down where rounding happens, because rounding per line and rounding per order are both defensible and they give different totals. That is a question for finance, not one for me to guess."
- Level 4: "Soft delete is a filter that has to be applied everywhere forever, so I put it where it can't be forgotten. And it's not privacy: if the data has to really go, this is the wrong tool."
- Level 5: "Without this, the last write wins and nobody knows anything was lost. With it, the conflict comes back to the person who can resolve it. `If-Match` being optional is a migration choice: I'd make it required once clients have caught up."
- Level 6: "A report that doesn't equal the sum of the rows it summarizes gets a support ticket the first day. So I sum the rounded amounts that clients already saw."

**What they would do next in production.**

- Move the idempotency keys to the database, written in the same transaction as the order, with a unique constraint on the key: two simultaneous retries must not both create. In memory, this service is safe only because one process handles one request at a time.
- Give keys an expiry, scoped to a client, since keys now grow forever.
- Enforce `version` in the database: `UPDATE ... WHERE id = :id AND version = :expected`, and treat zero rows as the 409. The check here and the write are separated by nothing only because this code is synchronous; once an `await` sits between them, two requests can pass the check together.
- Compute the report from a read replica or a rollup table as data grows, because it reads everything, and watch the rule "the report equals the rows" when it stops being computed live.
- Add an audit row for each change, with who and when, which would also answer finance's question about last month.

### Correctness

`POST` with a key reaches `create` only when the key is new. A successful create stores a deep copy of its answer, so a replay is the same bytes after any later change. A failed create throws before `remember`, so the key stays free. Canonical JSON gives one text per JSON value, so key order and spacing can't make a retry look like a different request.

`parseChanges` throws before `update` runs, and `update` applies all changes at once, so a refused request changes nothing. It raises `version` only when a value differs, so `version` counts real changes, which is what makes `If-Match` meaningful.

Every factor in `orderCost` is a whole number, and the products stay far below `2^53`, so `2 * dividend + divisor` is exact. Division happens once, then `Math.floor`, which is exact half-up rounding for positive whole numbers.

`get` and `list` read only rows that aren't deleted, and every route under `/work-orders/:id` goes through `requireOrder`, so a deleted order is a 404 everywhere.

The report builds its rows from `sites.list()`, so every site has one, in directory order. Each row adds the values `orderCost` returns for its live orders, and `totals` adds the rows, so the report equals the per-order costs by construction.

### Complexity

- Time: O(n + p) per report or list request; O(p) per other request — the report looks at each order and its part lines, and a list copies the live rows. A read by id scans the table once, and a cost scans the part lines. Indexes would make these cheaper in a real database.
- Space: O(n + p + k) — one row per order, one per part line, and one frozen answer per key.

### Trade-offs

- Storing a computed total on the order would make reads cheaper, and then every write has to remember to update it. Computing on read can't drift. Move to stored rollups only when reads are measurably too slow.
- Replaying the frozen answer against re-reading the current order: frozen is what the client was promised. Re-reading is simpler and surprising after an edit.
- A 422 for a reused key could be a 409, and teams differ. What matters is that it isn't a silent replay of the wrong thing.
- `BigInt` would make the money arithmetic safe at any size, at the cost of every number in the model. For sums this far below `2^53`, plain numbers are exact as long as you stay in whole numbers.
- Refusing unknown keys on `PATCH` (as here) catches typos such as `assigne`, which would otherwise answer 200 and do nothing. The cost is that a newer client can't send a field an older server doesn't know.

### Pitfalls and edge cases

Each wrong approach below was run against the hidden cases named with it, and each fails them.

- **Comparing raw body text for the same request.** A retry with its keys in another order looks like a conflict. Caught by `h1`.
- **Reading the header with its usual spelling.** `headers.get("Idempotency-Key")` finds nothing, because names are lower case here, as they are in Node. Caught by `ex1` and `h2`.
- **Remembering refused requests.** The fixed retry is then told about the old failure. Caught by `h5`.
- **Validating fields before looking the key up.** Caught by `h8`.
- **Storing the live object.** A replay after an edit shows the edit. Caught by `h18`.
- **`if (body.assignee)` to detect a change.** `null` can never clear an assignee. Caught by `ex3`.
- **`body.laborMinutes || order.laborMinutes`, or a truth test.** `0` is ignored. Caught by `h11`.
- **`{ ...order, ...body }` as the update.** Anything a client sends lands on the order. Caught by `h14`.
- **Applying fields as you validate them.** A refused request leaves a half-done change. Caught by `ex4` and `h15`.
- **Raising `version` on every accepted `PATCH`.** Caught by `h13`.
- **`minutes / 60 * rate`.** Caught by `h21`.
- **`minutes * (rate / 60)`.** Caught by `h22`.
- **`subtotal * 1.025`.** Caught by `h23`.
- **`Math.floor` where the rule is half up.** Caught by `ex6`.
- **Rounding the markup per line.** Caught by `h24`.
- **Storing the cost on the order at write time and not updating it.** Caught by `h25`.
- **A truth test on `quantity` or `unitCostCents`.** A free part is valid, and 0 is not a quantity. Caught by `h26`.
- **Numbering lines across all orders.** Caught by `h28`.
- **`if (query.get("includeDeleted"))`.** `"false"` is truthy. Caught by `h30`.
- **Filtering deleted rows in the list route only.** The other routes still find the order. Caught by `ex7` and `h31`.
- **Next id from the number of rows.** An id comes back. Caught by `h33`.
- **`expected !== order.version` with the header's raw text.** `"1" !== 1` makes every request stale. Caught by `ex10` and `h37`.
- **`Number(header)` without a format check.** `Number("")` is 0, and `Number("1.0")` is 1. Caught by `h36`.
- **Reading the body before checking the version.** Caught by `h38`.
- **Starting the report from the orders.** A site with none disappears. Caught by `ex11` and `h44`.
- **Rounding once over a site's summed minutes.** The report no longer equals its rows. Caught by `h41`.
- **Rounding the markup over a site's summed parts.** Caught by `h42`.
- **Counting deleted orders in the report.** Caught by `ex12` and `h43`.
- Project traps: `src/server.ts` must export `WorkOrderApi` by name; local imports need their `.ts` extension; `enum`, `namespace` and constructor parameter properties make Node refuse the file before any test runs.
