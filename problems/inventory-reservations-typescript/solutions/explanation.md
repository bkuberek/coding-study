# Inventory Reservations (TypeScript): Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | per request | per request | default answer: every rule a race could break is settled by the database, with a primary key, row locks taken in one order, and conditional updates |

## How the project grows level by level

| Level | New requirement | What the code adds |
|-------|-----------------|--------------------|
| 1 | Reserve, show and release, with what is available computed | `0002_reservations.sql`, `reservationRequest` in `src/requests.ts`, `reserve`, `reservation` and `release` in `src/reservations.ts` |
| 2 | Bursts of checkouts at once | Nothing new to answer: the transaction in `reserve`, the primary key that `claimOrder` relies on, the `FOR UPDATE` in `takeStock`, and the single conditional `UPDATE` in `release` were already the way to write level 1 |
| 3 | Holds that expire, whole orders, no deadlocks | `hold_seconds` and `expires_at`, the `HELD` expression that counts only live holds, and the sorted locking in `takeStock` |
| 4 | Stock per warehouse, by a migration that keeps every row | `0003_warehouses.sql`, `warehousesOf` and `receive` in `src/inventory.ts`, and a warehouse on each item |

## Approach: reference (Settle every race where the database settles it: a key, a row lock, one conditional update)

### Intuition

Every bug in this problem has the same shape: read, decide in the app, write. The read is a fact about the past by the time the write lands, because twenty other requests read the same row in between. The database is the one place that sees every request in order, so the decision has to be made there, at the moment of the write, not in the app a few milliseconds earlier.

Postgres gives three ways to do that, and the reference uses each where it fits. A primary key on the order id is the rule "one reservation per order": the second insert of the same id waits for the first transaction and fails if it committed, which no check in the app can do. A row lock, `SELECT ... FOR UPDATE`, makes every reservation of the same product queue behind the one that holds it, so what it reads after the lock stays true until it commits. And a release is a single `UPDATE ... WHERE status = 'active'`: of ten releases at once, exactly one finds the row active.

What is available is computed, never stored twice: stock minus what live holds keep. That makes expiry free, since a hold whose time has passed simply stops counting, with no job to run and no row to update. It also means a release changes one row and gives back exactly what it held.

Locks taken in different orders deadlock, and Postgres breaks a deadlock by failing one transaction. So every reservation locks its rows in one order, by SKU and then warehouse, and two orders that list the same products differently queue instead.

The migration is the last lesson. A schema change in production runs on rows nobody wrote the migration for, so it copies the old data into the new shape before dropping anything, and gives new columns defaults that make the existing rows valid.

### Say it out loud

"Reading the stock and then updating it from the app is a race: every concurrent checkout reads the same number. So I make the database decide. A reservation is one transaction: insert the order, whose primary key refuses a second reservation of the same order even when both arrive at once; lock each product row it takes stock from with `FOR UPDATE`, always sorted by SKU so two orders cannot deadlock; then read what is available, which no one can change while I hold the locks, and either insert the items or roll everything back.

"Available is stock minus active holds that have not expired, computed in the query. Expiry needs no job: a hold past its time stops counting. A release is one conditional update, so only one of many concurrent releases succeeds.

"For warehouses I write a migration that creates the new table, copies every product's stock into main, gives the item table a warehouse column that defaults to main for the rows already there, and only then drops the old column, all in one transaction."

### Algorithm

1. `POST /reservations`: check the body against the statement's rules, then that every SKU and warehouse exists, without a transaction since products and warehouses never disappear.
2. Begin a transaction. Insert the order with `ON CONFLICT DO NOTHING`; no row inserted means it was already taken: roll back, 409 `order_exists`.
3. Lock each `(warehouse, sku)` stock row, sorted by SKU and warehouse, with `SELECT ... FOR UPDATE`.
4. For each item, read on hand minus what live holds keep there. If any falls short, roll back, 409 `insufficient_stock`, which also frees the order id.
5. Insert the items and commit: 201.
6. `DELETE /reservations/{order}`: `UPDATE reservations SET status = 'released' WHERE order_id = $1 AND status = 'active' AND expires_at > now()`. One row updated is a release; otherwise the order is unknown, 404, or no longer active, 409.
7. `GET`: the status is `expired` for an active hold whose `expires_at` has passed, and as stored otherwise.

### Design

| File | Holds |
|------|-------|
| `migrations/0002_reservations.sql` | `reservations`, keyed by order, with its status and `expires_at`, and `reservation_items`, keyed by order and SKU |
| `migrations/0003_warehouses.sql` | `warehouses`, `warehouse_stock` filled from `products.stock`, a `warehouse` column on items that defaults to `main`, then `products.stock` dropped |
| `src/db.ts` | The pool, and `inTransaction`, which commits what returns and rolls back what throws; `GiveUp` rolls back with an answer |
| `src/requests.ts` | The statement's field rules, as functions that answer a typed request or nothing |
| `src/inventory.ts` | `HELD`, the common table expression of live holds per warehouse and SKU, and the product, warehouse and receipt routes |
| `src/reservations.ts` | `reserve` with `claimOrder` and `takeStock`, `reservation`, and `release` |

`inTransaction` keeps `BEGIN` and `COMMIT` on one connection from the pool: two `pool.query` calls can land on two connections, and then they are not one transaction, which is the easiest way to write a lock that locks nothing.

Every check that does not need the transaction happens before it, so a request that is malformed or names an unknown product never takes a lock. The order is claimed before stock is locked, so a duplicate order waits on the key and never holds a stock row while waiting.

### Correctness

Two reservations of the same product both lock its stock row, so they run one after the other: the second reads what is available only after the first committed or rolled back, and under Postgres's default `READ COMMITTED` that read sees the first one's items. So the sum of live holds on a row never exceeds its stock. Locks are taken in one total order, by SKU and warehouse, so no two transactions wait on each other in a cycle, and no deadlock can fail a reservation. An order id is claimed by inserting its primary key, which Postgres keeps unique across concurrent transactions. A release updates one row with the condition in its `WHERE`, and Postgres re-checks that condition after waiting for a concurrent update of the row, so of concurrent releases only the first updates it. A hold counts only while `expires_at > now()`, so an expired hold gives back exactly what it held, once, with nothing to write. The migration runs in one transaction and copies before it drops, so it either leaves the old schema whole or every product's stock in `main`.

### Complexity

- Time: per request — a reservation locks one row per item and sums the live holds of each, which an index on items by warehouse and SKU keeps to that product's holds
- Space: per request — one row per reservation and per item; expired and released reservations stay, as history

### Trade-offs

Row locks make concurrent checkouts of one product wait in line, which is right for correctness and becomes the bottleneck on a sale of one hot product. The alternative is an `UPDATE warehouse_stock SET on_hand = on_hand - $1 WHERE ... AND on_hand >= $1`, which decides in one statement and stores what is left instead of computing it. It is shorter for one item, and it makes expiry a write: some request or job must give the stock back exactly once, which is a race of its own. Computing availability keeps every hold as the single source of truth, at the cost of summing holds on each reservation.

`SERIALIZABLE` isolation would let the reservation read without locking and have Postgres refuse whichever of two conflicting transactions commits second. The service must then retry refused transactions, and under a burst most of them retry. Locks queue the same work without wasted attempts.

A `CHECK (on_hand >= 0)` constraint guards the stored number against any bug that would make it negative, and the reference keeps one. A constraint cannot express "holds never exceed stock" across tables, which is why the locks are still needed.

The level 4 migration rewrites the stock in one transaction, which is simple and safe at this size. On a large table it would lock writers for minutes: real migrations add the new table, backfill in batches, switch reads over, and drop the old column in a later release.

### Pitfalls and edge cases

**Wrong approaches.** Each fails a hidden case, and the failure names what it did. Parallel cases send their burst at once, behind a barrier, and repeat three times from a fresh database, so a race that loses only now and then still fails. None of these are stored as solutions: a pass of a parallel case finds no race and proves none, and the broken solutions are checked by hand until the grader's D7 runs them.

| What it does | Why it is wrong | What catches it |
|--------------|-----------------|-----------------|
| Reads what is available, compares it in the app, then inserts the hold or updates the stock | Every request of the burst reads the same number before any writes | `v6`, `h20`, `h21`, `h37`, `h38`, `h59` on their first run: `20 requests at once: expected 3 to answer 201 and 17 to answer 409; 9 answered 201 and 11 answered 409`, and `after GET /products/lamp: body.available: expected 0, got -6` |
| Checks `stock > 0` rather than `stock >= quantity` | One lamp left lets an order of two through | `h21` |
| Looks the order up, then inserts it, with no primary key or unique constraint | Ten copies of one order all find nothing and all insert | `v7`, `h23`: `expected 1 to answer 201 and 9 to answer 409` |
| Reads a reservation's status, then updates it, on a release | Ten releases at once all see it active | `h22`: `expected 1 to answer 200 and 9 to answer 409`, and with stored stock, the lamps come back ten times |
| Runs `BEGIN`, the locks and `COMMIT` through `pool.query` | Each query may take another connection, so nothing is locked for the next | `h20`, like the first row |
| Locks each item's row in the order the request lists them | Two orders listing the same products in opposite orders deadlock, and Postgres fails one with a 500 | `v10`, `h36`: `10 requests at once: expected 10 to answer 201; 1 answered 201 and 9 answered 500` |
| Holds each item in its own statement, outside one transaction | A later item that falls short leaves the earlier ones held | `v9`, `h37`: `after GET /products/desk: body.available: expected 2, got 1` |
| Stores what is left, and gives back expired holds from whichever request notices, with a read then an update | Several requests notice the same expired hold and each gives its stock back | `h38`: more than 3 of the 10 succeed |
| Gives back expired holds with `UPDATE products ... FROM` a join over their items | An `UPDATE ... FROM` applies one matching row per target, so two expired holds of one product give back one | `h38` |
| Treats a hold of 0 seconds as no hold, or lets an expired order id be taken again | The statement keeps the id, and a hold of 0 is a hold that already ran out | `h39`, `v8` |
| Level 4 migration that creates `warehouse_stock` and drops `products.stock` without copying it | Every product, the hidden ones included, ends with nothing | `v11`, `h50`: `body[0].available: expected 7, got 0` |
| Level 4 migration that copies the stock but adds `warehouse` to items as `NOT NULL` with no default | It fails on the items already there, so `bootstrap` fails, here and on every database with a reservation | The run stops at `bootstrap`, with node-pg-migrate's error |
| Creates `north` with a stock row only once something arrives, and locks only rows that exist | A reservation from `north` before any receipt finds no row to lock | `h58` |

**Edge cases.**

- An order refused for lack of stock holds nothing and frees its id, since the rollback undoes the insert of the order too (`v9`, `h37`).
- An order that names an unknown product is 404 before anything is locked or claimed (`h7`, `h40`).
- An expired order's id stays taken, and `DELETE` of it is 409, not 404 (`h31`, `h39`).
- `hold_seconds` of `"60"` is text, not a number, and 3601 is past the hour (`h32`, `h33`). A hold left out is 900 seconds, so it does not expire during a case (`h34`).
- Items come back listed by SKU, whatever order the request gave them in (`h10`).
- `quantity` of `1.5` is not whole (`h17`), and `x-fan` exists with no stock, which is 409, not 404 (`h18`).
- The hidden products are in `products` before your migrations run, and the level 4 cases ask for them by SKU (`h2`, `h50`, `h57`).
