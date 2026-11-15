# Review: Report Query: Rubric

## Finding the issues

- [ ] Flags `findAll()` loading the whole orders table and filtering in memory.
- [ ] Flags the N+1 queries from lazy `items` and `customer`, with an estimate of the query count.
- [ ] Flags the quadratic refund matching and quantifies it.
- [ ] Flags the missing indexes on the new `refunds` table and explains that foreign keys are not indexed automatically.
- [ ] Notices that nothing writes new refunds to the `refunds` table after the backfill.
- [ ] Flags floating-point money in the entity, the migration and the report row.
- [ ] Flags month boundaries computed in UTC instead of the merchant's time zone.
- [ ] Flags the unbounded response size and the 500 on an invalid month.
- [ ] Notes that the test cannot detect any of the performance problems.

## Prioritization

- [ ] Treats the whole-table load as the blocker that makes the endpoint fail on first use.
- [ ] Ranks correctness problems (missing refunds, money type) alongside the performance majors.
- [ ] Keeps Kotlin idioms as nits.

## Actionable comments

- [ ] Proposes pushing filtering and aggregation into one SQL query that uses the existing indexes.
- [ ] Warns about row multiplication when joining items and refunds in one aggregate.
- [ ] Gives the exact indexes to add and when `CREATE INDEX CONCURRENTLY` is needed.
- [ ] Suggests a query-count assertion to keep N+1 from coming back.

## Tone and collaboration

- [ ] Uses the production numbers from the context to explain impact instead of asserting "this is slow".
- [ ] Acknowledges the motivation for a dedicated refunds table.

## Asking about intent

- [ ] Asks whether refunds belong to the order's month or the refund's month.
- [ ] Asks how writers will move to the `refunds` table (dual write, backfill order).
- [ ] Asks whether the report should be synchronous or an asynchronous export.
