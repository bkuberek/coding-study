# Review: Report Query

## Context

A marketplace's merchant dashboard is a Kotlin Spring Boot service using Spring Data JPA (Hibernate) on Postgres, with Flyway migrations. Merchants have asked for a monthly sales report listing every order of the month with its item total, refunds and net amount. This pull request adds the report and a dedicated `refunds` table.

Facts about the codebase that are not visible in the diff:

- `orders` has 200 million rows and an index on `(merchant_id, created_at)`; `order_items` has 900 million rows and an index on `order_id`.
- The `Order` entity has `merchantId`, `createdAt: Instant`, `@ManyToOne(fetch = LAZY) customer` and `@OneToMany(mappedBy = "order") items` (lazy by default); `OrderItem` has `unitPrice: BigDecimal` and `quantity: Int`. Money elsewhere in the codebase is `BigDecimal` in Kotlin and `NUMERIC(12, 2)` in Postgres.
- The largest merchants have about 300,000 orders a month and about 1 million refunds in total.
- Today `RefundService` records a refund as a row in `order_adjustments` with `kind = 'refund'` and a negative amount. About 6 million such rows exist.
- Each merchant has a time zone setting; the dashboard shows dates in it.
- The service runs with a 2 GB heap; requests time out after 30 seconds.

## Pull request

**Monthly sales report**

> Adds `GET /merchants/{id}/reports/monthly?month=2026-03` returning one row per order with item total, refunded amount and net. Introduces a `refunds` table (backfilled from `order_adjustments`) because querying adjustments was awkward. Test covers an order with a refund.

## Task

Review the change as you would a teammate's pull request, in about 30 minutes. For each issue, give its location, its severity (blocker, major, minor or nit), what goes wrong at production data sizes and the change you would ask for. Ask about intent where the right fix depends on it. End with your overall verdict.
