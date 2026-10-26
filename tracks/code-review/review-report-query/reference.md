# Review: Report Query: Reference

Verdict: request changes. The report loads the entire orders table into a 2 GB heap, so the first call fails (and can take the instance down with it); after that is fixed, it still issues hundreds of thousands of queries and a quadratic merge for large merchants. The data-access shape needs to change from "load entities and loop" to "ask the database for the report". A strong review quantifies each problem with the production numbers in the context, proposes a single query, and catches that nothing writes to the new `refunds` table after the backfill.

A query to suggest (one round trip, served by existing and new indexes):

```sql
SELECT o.id, c.name,
       (SELECT SUM(i.unit_price * i.quantity) FROM order_items i WHERE i.order_id = o.id) AS items_total,
       (SELECT COALESCE(SUM(r.amount), 0) FROM refunds r WHERE r.order_id = o.id)         AS refunded
  FROM orders o
  JOIN customers c ON c.id = o.customer_id
 WHERE o.merchant_id = :merchantId
   AND o.created_at >= :monthStart AND o.created_at < :nextMonthStart   -- in the merchant's time zone
 ORDER BY o.id
```

Joining `order_items` and `refunds` in the same `GROUP BY` instead would multiply rows (every item times every refund) and inflate both sums; correlated subqueries or pre-aggregated subqueries avoid that.

## Blocker

- `SalesReportService.kt:26` `orders.findAll()`: loads all 200 million orders as managed entities and filters them in memory. It cannot fit in a 2 GB heap; the request dies with `OutOfMemoryError`, which can take down every request on the instance, after pulling the whole table over the network. Filter in the database by merchant and date range so the `(merchant_id, created_at)` index is used: a derived query `findByMerchantIdAndCreatedAtGreaterThanEqualAndCreatedAtLessThan`, or better the single report query above.

## Major

- `SalesReportService.kt:33` and `:38` N+1 queries: `order.items` and `order.customer` are lazy, so each order triggers one query for its items and, for each new customer, one for the customer. For a merchant with 300,000 orders that is up to 600,000 queries per report, far beyond the 30 s timeout. Fetch in bulk (`JOIN FETCH` or an `@EntityGraph`), or better, project only the needed columns with one query and no entities.
- `SalesReportService.kt:34` quadratic merge: for every order, `merchantRefunds.filter { it.orderId == order.id }` scans all of the merchant's refunds. 300,000 orders times 1 million refunds is 3 x 10^11 comparisons. Group once (`merchantRefunds.groupBy { it.orderId }`, then a map lookup), or let the database aggregate. `findByMerchantId` also loads every refund the merchant ever had, not just those of this month's orders.
- `V42__create_refunds.sql:1-7` missing indexes: Postgres does not index foreign-key columns automatically. `findByMerchantId` (and any per-order refund lookup) becomes a sequential scan of the refunds table on every report, and deleting or updating an order must scan `refunds` to check the foreign key. Add `CREATE INDEX ON refunds (order_id)` and `CREATE INDEX ON refunds (merchant_id, created_at)` in this migration (on a new, empty table a plain `CREATE INDEX` is fine; on an existing large table use `CREATE INDEX CONCURRENTLY` in its own non-transactional migration).
- New refunds are never written to `refunds`: the migration backfills from `order_adjustments`, but `RefundService` still writes only to `order_adjustments`. From the moment this deploys, every new refund is missing from the report, silently. Either dual-write in `RefundService` in this PR (with the backfill made idempotent and run after dual-writing starts), or read from `order_adjustments` until the migration of writers is planned. Ask which the author intended.
- `Refund.kt:19` and `V42__create_refunds.sql:5` money as floating point: `Double` / `DOUBLE PRECISION` cannot represent most cent amounts exactly, sums drift, and `ReportRow.net` mixes `BigDecimal.toDouble()` with `Double` (`SalesReportService.kt:41`). Everywhere else money is `BigDecimal` and `NUMERIC(12, 2)`; use the same, and keep `refunded` and `net` as `BigDecimal`.
- Refund period semantics (`SalesReportService.kt:34`): refunds are attributed to the month of the order, whenever they happened. A refund issued in April for a March order changes the March report after it was downloaded, so reports are not reproducible, which matters if merchants use them for accounting. Ask product whether the report should show refunds by order month or by refund month; accounting usually wants the latter.

## Minor

- `SalesReportService.kt:27` time zone: month boundaries are computed in UTC, but merchants see dates in their own time zone, so orders placed near midnight on the first or last day of a month land in the wrong report. Compute `[monthStart, nextMonthStart)` in the merchant's zone and convert to `Instant` for the query.
- Response size: one JSON array of up to 300,000 rows is built in memory and sent in one response. Stream it (CSV with a streaming response, or a paged API), or generate reports asynchronously and let merchants download the file.
- `ReportController.kt:16` `YearMonth.parse(month)`: an invalid `month` throws `DateTimeParseException` and becomes a 500. Bind it as `@RequestParam month: YearMonth` (with a converter) or validate and return 400.
- `V42__create_refunds.sql:9-14` backfill: 6 million rows copied inside the migration transaction delays the deploy and is not repeatable. Ask whether to move it to a batched, idempotent job.
- `SalesReportServiceTest.kt`: one order and one refund cannot catch any of the problems above. Add a query-count assertion (Hibernate statistics or a datasource proxy) to lock in the fix for N+1, orders of other merchants and other months (including boundaries in the merchant's time zone), and refunds of orders outside the month.

## Nit

- `SalesReportService.kt:31-44`: `mutableListOf` plus a `for` loop is `monthOrders.map { ... }` in idiomatic Kotlin.
- `SalesReportService.kt:45`: sorting in memory is unnecessary once the query has `ORDER BY o.id`.
- `Refund.kt:23`: the repository interface lives in the entity file; other modules keep repositories in their own files.
- `ReportRow` mixes `BigDecimal` and `Double`; with the money fix above, every amount has one type.
