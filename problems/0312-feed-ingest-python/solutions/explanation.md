# Feed Ingest (Python): Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | per feed | per feed | default answer: rows are checked in code and loaded by id inside one transaction, points are derived when asked, and the partner is called through one function that cannot raise |

## How the project grows level by level

| Level | New requirement | What the code adds |
|-------|-----------------|--------------------|
| 1 | Text to rows | `lines_of`, `parse_cents` and a row type in `src/feeds.py`; an `INSERT` in `src/ingest.py` |
| 2 | Bad rows named, loads repeatable | `check_row` and `read_feed` return a reason for each refused line; `migrations/0002_feeds.sql`; `ON CONFLICT DO NOTHING RETURNING`, a row lock for the feed and a stable insert order |
| 3 | Points in whole cents | `src/points.py`, a pure function over a member's purchases; `src/members.py` reads them each time |
| 4 | A partner that fails | `fetch_bonus` in `src/bonus.py`; `src/reconcile.py` and `migrations/0003_reconciliations.sql`; the statement |

## Approach: reference (Validate in code, load by id in one transaction, derive points on read, retry within bounds)

### Intuition

A feed is untrusted text, and the database is where trust lives. Every rule the table enforces (a real date, a known category, a non-negative amount, a unique id) is a rule the service must check first, because a violated constraint inside a transaction fails the whole feed, and one bad line should not cost the shop its other 199. So the service reads the text into good rows and named rejects, and only good rows reach the database.

Repeating a load is then a question of identity. A purchase is its id. Storing it with `INSERT ... ON CONFLICT (id) DO NOTHING RETURNING id` makes the database the judge of "new or already there", in one statement, with no window between a check and a write. That one habit gives all the properties of level 2 together: the same file twice stores once, a crash halfway is repaired by sending the file again, and two loads at once cannot create a duplicate.

Points are a function of a member's purchases in date order, and a purchase may arrive after later ones. A stored total would need repair on every late arrival, so nothing is stored: the function runs on the rows each time. It is a few dozen purchases of arithmetic, and it can be wrong in no way the rows are not.

The partner is the one part of the system that does not belong to you, so its failure is a value. `fetch_bonus` returns a bonus or `None` and cannot raise for anything the partner does. The run loops over members and stores `pending` for a `None`. A lookup that gave up costs a few seconds, not the run.

### Say it out loud

"I check each line in a function that returns either a good row or one reason, in the order of the rules, so the first problem is the one reported and I can test every rule without a database.

"The database decides what is new. I insert with `ON CONFLICT DO NOTHING RETURNING id`: a row comes back only if the insert stored it. Counting those gives `loaded`, and the rest of the good rows are `existing`.

"A load is one transaction. It first locks a row for the feed's name, so two loads of the same feed take turns and the report is rewritten whole, never mixed. It inserts in id order, so two loads of different feeds that share ids queue for each other's row locks in the same order and cannot deadlock.

"Amounts are strings turned into integers by splitting at the point. There is no float anywhere: `0.29 * 100` is `28.999999999999996`.

"Points are not stored. I sort the member's purchases by date and id, keep a running total per month and category, split each purchase across the bands with integer arithmetic, and divide once at the end of the purchase.

"For the partner I keep the policy small and fixed: three attempts, a one second limit on each, a pause that doubles from 200 ms, `Retry-After` when it asks for longer, no retry for a request that will not change, and `None` after the last failure."

### Algorithm

1. Split the body on `\n` only, and drop one trailing `\r` from each line. The first line must be the header, or the feed is refused with 400.
2. For each later line, skip it if it is empty, count it, and check it: five fields, non-empty id and member, a real date, a known category, an amount. The first rule broken is its reason. A line whose id an earlier good line already used is `duplicate_id`.
3. In one transaction: insert the feed's name if new and lock its row; delete its old rejects and write the new ones; insert the good rows sorted by id, counting those that came back from `RETURNING`.
4. Answer with `rows`, `loaded`, `existing = good rows - loaded`, and the number of rejects.
5. For points, read the member's rows, sort by `(date, id)`, and for each purchase split the cents `before .. before + amount` over the category's bands. Sum `cents * percent` and add `weighted // 10000`.
6. For a reconciliation, list the month's members, skip those already reconciled, and for each call `fetch_bonus`: a number is `reconciled`, `None` is `pending`. Answer with the counts.

### Design

- `src/server.py`: routes and JSON in and out. It decodes bodies, picks a function and shapes the answer, and holds no rule.
- `src/feeds.py`: `lines_of`, `parse_day`, `parse_cents`, `check_row` and `read_feed`: pure, so every rule of level 2 has a unit test with no database.
- `src/ingest.py`: `load_feed` and `rejects_of`, the only code that writes feeds. `store` runs inside the transaction `load_feed` opens.
- `src/points.py`: the bands as data, `weighted_cents` for one purchase and `points_per_month` for a member.
- `src/members.py`: reads a member's rows, and builds the points answer and the statement.
- `src/bonus.py`: `fetch_bonus` with the opener and the sleep as arguments, so the retry policy is tested in milliseconds.
- `src/reconcile.py`: the month's members, the skip of those done, and the upsert of each outcome.
- `migrations/0002_feeds.sql` and `0003_reconciliations.sql`: the report and the statuses, each with the constraints that make a wrong state unrepresentable.

Not graded, and worth discussing:

- **Streaming and batches.** The reference reads a feed whole and inserts row by row. A feed of millions would be streamed, validated as it goes, and loaded in batches of a few thousand with a multi-row `INSERT` or `COPY` into a staging table followed by one `INSERT ... SELECT ... ON CONFLICT DO NOTHING`.
- **Jitter and a breaker.** A hundred copies of this service retry in lockstep after an outage. Random jitter spreads them out, and a circuit breaker stops asking a partner that is clearly down.
- **A cap on `Retry-After`.** The reference trusts the header. A partner that asks for an hour would hold a request for an hour; a real client gives up when the wait is longer than the request's budget.
- **Two reconciliations at once.** Both would ask about the same pending members. `SELECT ... FOR UPDATE SKIP LOCKED` on the member's row, or an advisory lock for the month, would let one of them go first.

### Correctness

Every row in `purchases` passed `check_row`, so the table's constraints can never fail a load. Loading by `ON CONFLICT (id) DO NOTHING` means the first row stored for an id stays, and a repeat changes nothing, so a feed sent any number of times has the effect of being sent once. `loaded + existing + rejected` equals `rows`. The lock on the feed's row and the sorted insert order mean concurrent loads are answered 200 and leave each purchase stored once, with a report that is one load's, whole.

Points are a pure function of the stored purchases, so they cannot depend on the order the feeds arrived in. `fetch_bonus` returns in at most `3 * 1 s` plus the pauses, and never raises for the partner's behavior, so `reconcile` ends with a count for every member.

### Complexity

- Time: per feed — linear in the lines, each line a constant number of checks and one indexed insert
- Space: per feed — the feed's text and its rows are held while they load

### Trade-offs

Validating in code duplicates what the table already enforces, which is the cost of reporting a reason per line. The alternative is to try each insert inside a savepoint and read the constraint name from the error: no duplicated rules, but a savepoint per row, reasons tied to constraint names, and no way to express `bad_date` for the text `20270301` that Postgres would happily read as a date.

Deriving points makes every read cost the member's whole history, in return for never being stale. A member with years of purchases would justify a table of monthly totals, rebuilt from the rows of any month an arriving feed touches.

Sequential lookups keep the run's worst case easy to state (members times three attempts) and the mock's log easy to read. Asking several members at once would cut the time and need a limit, so the partner is not hit by a burst of its own customers.

### Pitfalls and edge cases

- **Check-then-insert.** A `SELECT` for the id followed by an `INSERT` has a gap in which a second load inserts the same id; the loser gets a unique violation and a 500. Hidden case `h20`, six copies of one file at once, catches it.
- **Unordered inserts.** Two feeds that share ids and insert them in opposite orders wait on each other's uncommitted rows and Postgres aborts one with a deadlock. Hidden case `h21` sends one feed ascending and one descending, eight at a time.
- **Rewriting the report without a lock.** Two loads of one name both delete the old rejects and insert the new ones, and the second insert hits the primary key. Locking the feed's row at the start fixes it.
- **Python reads more than you meant.** `str.splitlines()` splits on `\x0b`, `\x1c` and ` `, which shifts every later line number (`h9`). `int()` and `\d` read digits of other scripts, so full-width `１２` is a number to them (`h8`, `h7`). `date.fromisoformat` accepts `20270301` and `2027-W09-1` (`h7`).
- **Floats in money.** `int(float("0.29") * 100)` is 28 (`h4`).
- **Empty lines are lines.** They are not rows, but the report counts them in a line number (`h12`).
- **A duplicate of a rejected row is not a duplicate.** A later line with the same id as a line that was refused for its date loads (`h11`).
- **Rounding.** Points are rounded down once for each purchase. Rounding per band, or on a member's total, gives other numbers (`h24`, `h25`).
- **Order within a day.** Ids compare as text, so `P10` is before `P9`, and the order changes the points when a purchase crosses a band (`h29`). Points taken in arrival order instead of date order differ the same way (`h30`).
- **A client with no timeout.** The `ana_slow` partner answers after 2 s, so a lookup that waits for it succeeds on the first request, where the rule says three timeouts and a pending member (`h35`).
- **A client with no retry.** The first 503 makes the member pending, where the rule reconciles after the second attempt (`v9`, `h34`).
- **A retry with no pause.** The partner's log shows the next request arriving at once; the cases require at least 150 ms between the attempts of a member (`v8`).
- **Retrying a 403.** It cannot change, and the log shows a second request that the rule forbids (`h37`).
- **Asking again for members that are done.** Running the reconciliation twice must not ask about a reconciled member again (`h41`, `h43`).
