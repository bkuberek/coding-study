# Feed Ingest (Python)

## Statement

A loyalty program gives its members points for what they buy. Every day each shop sends the program a *feed*: a plain text file with one line for every purchase. Your service takes those files in, keeps the purchases in Postgres, and works out how many points each member has earned.

Files that come from outside are never quite clean. A date that is not a date, an amount that is not a number, a category nobody has heard of, the same purchase twice, or the same file sent again because a shop was not sure the first one arrived. The core idea of this problem is turning untrusted text into rows you can trust, in a way that is safe to repeat: **sending a file twice must leave the database exactly as sending it once did.**

You build it in four levels. Level 1 only needs you to read a file line by line and put rows in a database, so it is a fine place to start if you have not done that before. Later levels bring in the rules a real feed needs: refusing bad rows and saying why, loading once however often a file is sent, counting money in whole cents, and calling a partner that is sometimes slow or down.

`cstudy` runs your service in a Docker sandbox with Postgres and a mock of the partner, and judges it by what its HTTP API answers and by what it asks the partner. The program, its shops and its members are invented.

## Input

A feed is CSV text. Its first line is the header, and each line after it is one purchase:

```text
id,member,date,category,amount
T1001,ana,2027-03-01,grocery,42.50
T1002,ana,2027-03-02,fuel,30
```

| Column | Meaning |
|--------|---------|
| `id` | The purchase's id, text. One id is one purchase, however many times it is sent |
| `member` | Who bought it, text |
| `date` | The day of the purchase, written `YYYY-MM-DD` |
| `category` | One of the codes in the `categories` table: `grocery`, `dining`, `fuel`, `travel` or `other` |
| `amount` | What was paid, in dollars with up to two decimals: `42.50`, `42.5` and `42` are all fine |

A line ends with `\n` or `\r\n`, and the last line may have no line break. A field is used exactly as written: no field is quoted, none holds a comma, and none is trimmed of spaces. A line with nothing at all on it is an empty line, and empty lines are skipped.

Money is held in whole **cents** everywhere, as an integer: `42.50` is `4250`. Never turn an amount into a float on its way there, because `0.29` has no exact float and a cent can go missing.

## Output

Every answer is JSON with `Content-Type: application/json`. A refusal has the form `{"error": "<code>"}`, with the code each level names. A path or a method no level describes answers 404 `{"error": "not_found"}`.

`PUT /feeds/{name}` loads the feed that is the request's body. `name` is the feed's name, such as `march-1.csv`: letters, digits, `.`, `_` and `-`. The answer is 200 and says what happened to the lines of the feed:

```json
{"feed": "march-1.csv", "rows": 5, "loaded": 3, "existing": 0, "rejected": 2}
```

| Field | Meaning |
|-------|---------|
| `rows` | The lines after the header that are not empty |
| `loaded` | Rows stored by this request that were not in the database before |
| `existing` | Good rows whose id was already stored, so nothing was stored |
| `rejected` | Rows refused, which the levels explain. Level 1 has none |

`GET /health` answers 200 once the app is ready, and your app reads its port from `PORT`.

## Project

`cstudy start` copies the service into `projects/feed-ingest-python/`, and `cstudy dev` runs it with Postgres and the partner's mock. It uses Python's standard library and `pg8000`, a small Postgres client written in Python.

- `src/server.py`: the routes. `GET /purchases` works already, and `PUT /feeds/{name}` answers 501.
- `src/db.py`: `connect()` and `query()`, which run SQL with named parameters (`:member`) so you never build SQL out of text.
- `migrations/`: the schema, as plain SQL files that `scripts/migrate.py` applies in name order before your app starts. `0001_purchases.sql` makes the `categories` and `purchases` tables. Add your own as `0002_...sql` and on, and never edit one that has run.
- `scripts/reset.py`: puts the database back as it was after the migrations, between cases. It works for any tables you add, so leave it as it is.
- `tests/`: your tests, run by `cstudy test`, with a fixture for the app and one for the partner.
- `vendors/bonus-partner/API.md`: the partner's contract, from level 4.
- `.env`: what your app reads, written by `cstudy start`. Your app's environment already holds it.

`cstudy test` starts a sandbox, runs your tests beside the app, and then the visible cases of your open levels. `cstudy submit` grades every case of the open levels, hidden ones included, and opens the next level when they all pass. Each submission grades the earlier levels again, so a later change must keep their answers. Every case starts from the database as the migrations left it, with no rows.

## Level 1: Load a feed

Two routes:

- `PUT /feeds/{name}`: read the feed in the body, check nothing yet, and store each row in `purchases`. The `amount` is stored as `amount_cents`.
- `GET /purchases?member=<id>`: the member's purchases, oldest first and by `id` within a day, as `[{"id": "T1001", "member": "ana", "date": "2027-03-01", "category": "grocery", "amount_cents": 4250}]`. A member with none is `[]`, and a request without `member`, or with an empty one, is 400 `{"error": "member_required"}`. This route works in the starter.

At this level every feed is good: its header is the one above, every row has five fields, a real date, a known category and an amount in dollars, and every id is new. A feed with a header and no rows loads nothing. The answer's `existing` and `rejected` are 0.

An amount becomes cents with whole-number arithmetic: the digits before the point times 100, plus the digits after it, padded on the right to two (`12.5` is `1250`, `12.05` is `1205`).

### Example 1

<!-- case: v1 -->

Three rows load, and each member asks for their own purchases. Ana's list is in date order, and `30` is 3000 cents.

### Example 2

<!-- case: v2 -->

The feed uses Windows line endings, has an empty line in the middle and no line break at the end. `120` is 12000 cents and `0.07` is 7.

## Level 2: Clean rows, loaded once

Now feeds are messy. Add the route `GET /feeds/{name}/rejects`, and make `PUT /feeds/{name}` safe.

**The header.** The first line must be exactly `id,member,date,category,amount`. Anything else, an empty body included, is 400 `{"error": "invalid_header"}`: nothing is loaded and nothing else changes.

**Rejecting rows.** A row that the table would not hold is refused, and the rest of the feed still loads. Each row is checked against these rules in this order, and is rejected for the first one it breaks:

| Reason | The row is rejected when |
|--------|--------------------------|
| `wrong_field_count` | It does not have exactly 5 fields |
| `empty_field` | `id` or `member` is empty |
| `bad_date` | `date` is not a real day written exactly `YYYY-MM-DD`, with ASCII digits. `2027-02-29`, `2027-3-1`, `20270301` and `2027-W09-1` are not |
| `unknown_category` | `category` is not a code in `categories`, compared exactly: `Grocery` is not `grocery` |
| `bad_amount` | `amount` is not digits with an optional point and one or two digits after it. At most 9 digits come before the point, at least one. No sign, no spaces, no thousands separator, no exponent. `5.`, `.5`, `1e3` and `12.345` are not |
| `negative_amount` | `amount` has a leading `-` and is otherwise written as above, a zero included: `-5` and `-0.00` |
| `duplicate_id` | An earlier line of this same feed passed all the rules above with the same `id`. The earlier line stays and this one is rejected |

Digits mean `0` to `9` only. A row whose earlier twin was rejected for another reason is not a duplicate. An amount of zero is a good amount.

**The reject report.** `GET /feeds/{name}/rejects` answers 200 with one entry for each rejected row of the feed's latest load, ordered by line: `[{"line": 3, "reason": "bad_date"}]`. `line` is the row's place in the file, where the header is line 1, counting the empty lines. A feed that loaded without a reject is `[]`, and a name no load has ever accepted is 404 `{"error": "unknown_feed"}`. Loading a name again replaces its report, and a load refused for its header leaves the report as it was.

**Loading once.** A purchase's `id` is its identity. A good row whose `id` is already stored, from this feed or another, is counted in `existing` and changes nothing: **the first row stored for an id is the one that stays**, even if a later feed sends the id with other values. So the same file sent again loads 0, finds the same rows existing, and writes the same report. Several loads may arrive at once, of the same feed or of feeds that share ids, and each must be answered 200 and leave every purchase stored once.

### Example 1

<!-- case: v3 -->

Three rows are refused: line 3 has a date that does not exist, line 4 a category in the wrong case, line 5 a negative amount. The two good rows load, and the report names the lines.

### Example 2

<!-- case: v4 -->

The same file is sent twice. The first answer loads 2 rows; the second finds both existing and loads none. The duplicated id on line 4 is rejected both times, and the report holds it once.

## Level 3: Points

Add `GET /members/{member}/points`: 200 `{"member": "ana", "points": 130}`, or 404 `{"error": "unknown_member"}` for a member who has no stored purchase. A member whose purchases all earn nothing is still a member.

A purchase earns points from its category's bands. Think of a member's spending in a category in one calendar month as a running total in cents. A band is a stretch of that total, and each cent of a purchase is worth the percent of the band it falls in, where 100 percent is one point for every 100 cents.

| Category | Spending so far this month | Percent |
|----------|----------------------------|---------|
| `grocery` | the first 20,000 cents | 200 |
| `grocery` | beyond | 100 |
| `dining` | the first 10,000 cents | 300 |
| `dining` | from 10,000 to 30,000 | 200 |
| `dining` | beyond 30,000 | 100 |
| `fuel` | the first 15,000 cents | 150 |
| `fuel` | beyond | 100 |
| `travel` | the first 50,000 cents | 400 |
| `travel` | beyond | 150 |
| `other` | all | 100 |

The rule, exactly:

1. A member's purchases are taken in order of `date`, and purchases on the same date in order of `id`, compared as plain text one character at a time, so `P10` comes before `P9`.
2. For each purchase, `before` is what the member spent in the same category in the same calendar month on the purchases taken earlier. The purchase covers the cents from `before` to `before + amount_cents`. Each of those cents is worth the percent of the band it falls in. A band ends where the next begins: the 20,000th cent is the last of the first grocery band.
3. `weighted` is the sum of the cents times their percents. The purchase earns `weighted // 10000` points: **rounded down, once for each purchase**, not for each band and not for the member's total.
4. A member's points are the sum over all their purchases, in every month. Months and categories keep separate running totals, so the bands start again on the first of each month.

For example, a grocery purchase of 3,000 cents when 19,000 are already spent this month covers 1,000 cents at 200 and 2,000 at 100: `(1000 * 200 + 2000 * 100) // 10000` is 40 points.

Use integers throughout. A purchase can arrive late, in a feed sent after feeds with later dates, and the answer must be the one the rule gives for all stored purchases in date order, whenever they arrived. A purchase counted twice, by being sent twice, earns once.

### Example 1

<!-- case: v5 -->

Ana's grocery purchase of 4,250 cents earns 85, and 3,000 cents of fuel earns 45: 130 in all. Ben's 1,890 cents of dining earns 56.7, rounded down to 56.

### Example 2

<!-- case: v6 -->

Ben's first dinner is 9,500 cents, all in the 300% band: 285 points. The second is 2,000 cents, of which the first 500 finish that band and the other 1,500 earn 200%: 45 points.

## Level 4: When the partner stumbles

A partner grants members bonus points each month, and a reconciliation asks it for each member's bonus. The partner is a separate service, reached at `BONUS_URL`, and it is sometimes slow, sometimes down, sometimes wrong. Its contract is in `vendors/bonus-partner/API.md`.

Add two routes:

- `POST /reconcile` with the JSON body `{"month": "2027-03"}`: the members to reconcile are those with at least one stored purchase dated in that month. For each of them, in order of member id as plain text, ask the partner `GET /v1/bonus?member=<id>&month=<month>` and record what it said. The answer is 200 `{"month": "2027-03", "members": 2, "reconciled": 1, "pending": 1}`, where `members` counts the members of the month, `reconciled` those whose bonus is known after this run, and `pending` the rest. A body without a `month` written `YYYY-MM` with a month from `01` to `12` is 400 `{"error": "invalid_month"}`.
- `GET /members/{member}/statement?month=2027-03`: 200 `{"member": "ana", "month": "2027-03", "points": 130, "bonus": 25, "status": "reconciled"}`. `points` is what the member's purchases dated in that month earn, the level 3 amounts for that month, with the bonus left out. `status` is `reconciled` with the `bonus` the partner granted, `pending` with `"bonus": null` when the partner could not be asked, or `open` with `"bonus": null` when no reconciliation has tried yet. An invalid `month` is 400 `{"error": "invalid_month"}`, and a member with no stored purchase at all is 404 `{"error": "unknown_member"}`. `GET /members/{member}/points` does not change.

**One failed lookup never fails the run.** A lookup follows these rules:

| Situation | What the service does |
|-----------|-----------------------|
| 200 with `{"bonus_points": <whole number, 0 or more>}` | The member is reconciled with that bonus |
| 404 | The partner has no record, and that is an answer: reconciled, bonus 0 |
| No answer within 1 second, a connection that fails or drops, a 5xx, or a 200 whose body is not as above | A failed attempt: try again, up to 3 attempts in all |
| 429 | A failed attempt as well. Wait for the longer of the backoff and `Retry-After` seconds before the next one |
| Any other 4xx | Not retried: the lookup ends at once |
| 3 failed attempts, or a 4xx that is not retried | The lookup gives up: the member is `pending`, and the run goes on with the next member |

The pause before the second attempt is at least 200 ms and before the third at least 400 ms: a backoff that doubles. A member who is already `reconciled` for the month is not asked again by a later run; a `pending` one is.

### Example 1

<!-- case: v7 -->

Ana and Ben are both reconciled: Ana's bonus is 25 and Ben's is 40. The partner was asked once about each.

### Example 2

<!-- case: v8 -->

The partner is down. Each member is asked three times, with a pause between the attempts, and the run still ends with a 200 that says both are pending. The statements show no bonus.

### Example 3

<!-- case: v9 -->

The partner fails once about Ana and then answers. Her second attempt comes after a pause, and she is reconciled. Nobody else is affected.

## Constraints

- Python 3.13 and its standard library, with `pg8000` for Postgres 17 at `DATABASE_URL`. The partner is at `BONUS_URL`.
- A feed's body is under 1 MiB, and feeds in the cases have under 200 lines. Amounts are at most 999,999,999.99.
- Money is an integer number of cents everywhere. Points are integers.
- Cases run one after another against your app and a database that each starts empty. A lookup that goes wrong takes the time its attempts take, a few seconds at most.

## Follow-ups

- This service reads a feed whole, in memory. How would you load a feed of 50 million lines? Think of streaming the body, loading in batches, `COPY` into a staging table and a single `INSERT ... SELECT ... ON CONFLICT`.
- A crash halfway through a load leaves part of a feed stored. Why does loading by id make that harmless, and what would you change if rows could not be repeated safely?
- Points here are worked out when asked. When would you store them instead, and what keeps a stored total right when an older purchase arrives late?
- A hundred copies of this service all retry the partner at the same moments after an outage. What does adding random jitter to the backoff do, and what does a circuit breaker add?
- The partner sends `Retry-After: 3600`. What should the service do?
- Two reconciliations of the same month start at once. What would stop them asking the partner about the same member twice?

## Hints

### Hint 1

A CSV file is only text. `text.split("\n")` gives you its lines, and `line.split(",")` gives you the fields of one line. Write a small function that takes the text and returns the rows as a list, and try it on its own with a short example before you touch the database. Skip the header line and any line with nothing on it.

### Hint 2

To store a row, run an `INSERT` with named parameters: `query("INSERT INTO purchases (...) VALUES (:id, :member, ...)", id=..., member=...)`. Never put values into the SQL with an f-string. The `date` column takes a Python `date`, made with `date.fromisoformat(text)` at this level, where every date is good.

### Hint 3

Do not use a float for an amount. Split the text at the point: `whole, _, fraction = text.partition(".")`. Then `int(whole) * 100 + int(fraction.ljust(2, "0") or 0)`.

### Hint 4

Write one function that takes a line and returns either the good row or the reason it is refused, checking the rules in the order of the table. It is easy to test, and the HTTP part stays small. Beware of Python's helpfulness, which here is a bug: `str.splitlines()` also splits on characters that are not `\n`, `int("١٢")` happily reads digits from other scripts, `\d` in a regular expression matches them too, and `date.fromisoformat("20270301")` accepts a form that is not `YYYY-MM-DD`.

### Hint 5

`INSERT ... ON CONFLICT (id) DO NOTHING RETURNING id` returns a row only if it stored one. That is how you tell `loaded` from `existing` without a separate `SELECT`, which would race with a load running at the same time. Do one whole feed inside one transaction (`START TRANSACTION` ... `COMMIT`).

### Hint 6

Two loads of the same feed both rewrite its report. Lock a row that stands for the feed (`SELECT ... FOR UPDATE`) at the start of the transaction, and they take turns. Two loads of different feeds that share ids can wait on each other's rows and deadlock, unless they insert in the same order: sort the rows by id first.

### Hint 7

Do not store points. Read the member's purchases, sort them by `(date, id)`, and walk them keeping a running total for each `(month, category)`. For each purchase split its cents between the bands, add up `cents * percent`, and divide with `//` once.

### Hint 8

A retry loop is a `for attempt in range(3)` with a `try` inside, a decision about which failures to retry, and a `time.sleep` before the next attempt that you skip after the last one. `urllib.request.urlopen(url, timeout=1)` bounds an attempt. Pass the opener and the sleep as arguments, so a unit test can give it a fake that fails twice and answers, and never really waits.

### Hint 9

Keep one function whose answer is a bonus or `None`, and never let it raise for what the partner does. The loop over the members then needs no `try`, and a member who gave up is just stored as pending. Skip the members that are already reconciled before you call it.
