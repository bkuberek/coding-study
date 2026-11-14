# Inventory Reservations (TypeScript)

## Statement

A shop holds stock for each checkout while the customer pays: the items are set aside, and nobody else can buy them until the checkout finishes, gives up, or runs out of time. On a quiet day that is a few rows in a table. On a sale day, twenty customers press "buy" on the last three lamps in the same second, and a service that reads the stock, decides, and then writes it back sells lamps it does not have.

Build the reservation service in levels, on Postgres. It reserves and releases stock, never sells more than there is however many checkouts arrive at once, lets holds expire, reserves an order of several items whole or not at all without deadlocking, and finally moves its stock into warehouses through a migration you design, without losing a row. `cstudy` runs your app and its database in a Docker sandbox and judges it by what it answers over HTTP, including bursts of requests sent at the same moment. The shop, its products and its numbers are invented.

## Input

HTTP requests with JSON bodies: `GET /products/{sku}`, and `POST /reservations`, `GET /reservations/{order}` and `DELETE /reservations/{order}` to reserve, read and release. Each level says what it adds.

## Output

JSON, always with `Content-Type: application/json`. A refusal is `{"error": "<code>"}`, with the codes each level names. Your app reads its port from `PORT` and listens on all interfaces inside the container (`0.0.0.0`), and `GET /health` answers 200 once it is ready.

## Project

`cstudy start` copies the service into `projects/inventory-reservations-typescript/`, and `cstudy dev` runs it with its database. Node runs the files by stripping their types, so write no `enum`, no `namespace` and no constructor parameter properties, and import your own files with their `.ts` extension.

- `src/server.ts`: the routes, and where the server starts. It answers `GET /products/{sku}` from the database already, and 501 to everything about reservations.
- `src/db.ts`: the connection pool, from `DATABASE_URL`.
- `migrations/`: the schema, as plain SQL files that node-pg-migrate applies in name order. `0001_baseline.sql` is the problem's and stays as it is; add yours after it, `0002_...sql` and on. Each file starts with `-- Up Migration`, and node-pg-migrate runs each in a transaction of its own and records it in `pgmigrations`.
- `scripts/reset.ts`: puts the database back as it was after your migrations, before a case that starts fresh. You should not need to change it.
- `tests/`: your tests, run by `cstudy test`.
- `.env`: what your app reads, written by `cstudy start` from the problem's settings. Your app's environment already holds it.

`cstudy test` starts a sandbox, applies the migrations, runs your tests beside the app, and then the visible cases of your open levels. `cstudy submit` grades every case of the open levels, hidden ones included, and opens the next level when they all pass. Each submission grades the earlier levels again, so a later change must keep their answers. To look at the data yourself while `cstudy dev` runs, `docker ps` shows its database container, whose name ends in `-db-1`, and `docker exec -it <that name> psql -U app` opens a shell on it.

### The data you start with and the data you do not see

`0001_baseline.sql` creates `products`, one row per product with its `stock`, and four products:

| SKU | Name | Stock |
|-----|------|-------|
| `lamp` | Desk lamp | 3 |
| `desk` | Standing desk | 2 |
| `chair` | Office chair | 40 |
| `mug` | Coffee mug | 40 |

The rest of the schema is yours to design. The cases never name a table: they ask your API.

When `cstudy submit` grades, it applies the baseline, then adds hidden products to `products`, and only then applies your migrations, so they run on a table that holds rows you never saw, as a migration in production does. SKUs that start with `x-` are reserved for those rows. A migration that loses them fails the cases that ask for them. Grading also applies your migrations to an empty database, which must work too.

A case that starts fresh gets the database as it was right after your migrations, and your app started again.

## Level 1: Reserve and release

`GET /products/{sku}` answers 200 with what can be reserved now: the stock, minus what active reservations hold.

```json
{"sku": "lamp", "name": "Desk lamp", "available": 3}
```

`POST /reservations` holds stock for one order:

```json
{"order": "o-1001", "items": [{"sku": "lamp", "quantity": 2}]}
```

| Field | Rule |
|-------|------|
| `order` | The order's id, 1 to 64 letters, digits, `-` or `_`. One reservation per order, ever |
| `items` | 1 to 10 items, each SKU at most once |
| `items[].sku` | A product's SKU |
| `items[].quantity` | A whole number from 1 to 100 |

It answers 201 with the reservation, its items listed by SKU:

```json
{"order": "o-1001", "status": "active", "items": [{"sku": "lamp", "quantity": 2}]}
```

`GET /reservations/{order}` answers 200 with the same shape, and `DELETE /reservations/{order}` releases it: the stock is available again, and it answers 200 with the reservation, now `"status": "released"`.

| Request | Status | Body |
|---------|--------|------|
| A body that is not a JSON object, or a field missing or breaking its rule | 400 | `{"error": "invalid_request"}` |
| An item whose SKU no product has | 404 | `{"error": "unknown_sku"}` |
| An order that already has a reservation, whatever its status | 409 | `{"error": "order_exists"}` |
| An item asking for more than is available | 409 | `{"error": "insufficient_stock"}` |
| `GET` or `DELETE` of an order never reserved | 404 | `{"error": "unknown_order"}` |
| `DELETE` of a reservation that is not active | 409 | `{"error": "not_active"}` |

A reservation is checked in the order of this table, and a refused one holds nothing. `GET /products/{sku}` of an unknown SKU is 404 `unknown_sku`.

### Example 1

<!-- case: v1 -->

The baseline's lamps, all available.

### Example 2

<!-- case: v2 -->

Two of the three lamps are held for order `v2`.

### Example 3

<!-- case: v3 -->

Order `v3` was reserved first, for 2 lamps, so 1 is left.

### Example 4

<!-- case: v4 -->

Order `v4` reserved 2 lamps and released them, so all 3 are back.

### Example 5

<!-- case: v5 -->

There are 3 lamps, and the order asks for 4.

## Level 2: Checkouts at once

Nothing new to answer: the same requests now arrive together. The cases send a burst of up to 20 requests at the same moment, and judge how many succeeded and what is available after. However the requests interleave, the service never holds more than the stock, an order is reserved at most once, and a reservation is released at most once.

Reading the stock, deciding, and then writing is the bug: between your read and your write, every other checkout read the same number. Let the database settle it. A row lock (`SELECT ... FOR UPDATE`) makes the others wait for your transaction; an `UPDATE` with the condition in its `WHERE` decides in one statement; a primary key or a check constraint refuses what must not happen. Your migrations may add any of them.

A burst's example shows the request it repeats, with `{i}` standing for each request's number, from 0, and the statuses expected, which can come back in any order.

### Example 1

<!-- case: v6 -->

Five checkouts at once for the last 3 lamps: exactly 3 succeed, and none are left.

### Example 2

<!-- case: v7 -->

The same order arrives five times at once: one reservation, of one mug.

## Level 3: Holds that expire and orders that hold together

`POST /reservations` takes `hold_seconds`, a whole number from 0 to 3600, and 900 when left out. Once that long has passed, the reservation is `expired`: it holds nothing, `GET` shows `"status": "expired"`, and `DELETE` is 409 `not_active`. A hold of 0 has run out by the next request, which is how the cases make a hold expire without waiting. Its order id stays taken.

An order of several items is held whole or not at all: if one item cannot be held, the answer is the refusal and no item is held.

Two orders that ask for the same products in different orders must both go through. If each locks its rows in the order its items came, one holds the lamp and waits for the desk while the other holds the desk and waits for the lamp, and Postgres ends that deadlock by failing one of them. Lock rows in one order every time, or retry what Postgres refused.

### Example 1

<!-- case: v8 -->

Order `v8` held all 3 lamps for 0 seconds, so they are available again.

### Example 2

<!-- case: v9 -->

There are 2 desks and 3 lamps. The order asks for 1 desk and 4 lamps, is refused, and holds no desk.

### Example 3

<!-- case: v10 -->

Ten orders at once, the even ones listing a chair then a mug and the odd ones a mug then a chair. All of them are held.

## Level 4: Warehouses

The shop opens a second warehouse. Stock is now kept per warehouse, `main` and `north`: write a migration that moves every product's stock to `main`, with `north` starting empty, and keeps every reservation taken so far as taken from `main`. The hidden products are in `products` before it runs, and must keep their stock.

| Request | Answer |
|---------|--------|
| `GET /products/{sku}/warehouses` | 200 with every warehouse, by code, and what is available in each: `[{"warehouse": "main", "available": 3}, {"warehouse": "north", "available": 0}]` |
| `POST /warehouses/{code}/receipts` with `{"sku": "lamp", "quantity": 4}` | Stock arrives: 201 with `{"warehouse": "north", "sku": "lamp", "available": 4}`, what is available there now. `quantity` is a whole number from 1 to 1000 |

An item may name its `warehouse`, and one that names none is taken from `main`. Available stock, and every rule of the earlier levels, now hold per warehouse, and `GET /products/{sku}` answers the total of all of them. Reservations still list their items as `sku` and `quantity`.

| Request | Status | Body |
|---------|--------|------|
| A receipt that is not a JSON object, or a field breaking its rule | 400 | `{"error": "invalid_request"}` |
| A warehouse that is neither `main` nor `north` | 404 | `{"error": "unknown_warehouse"}` |
| A receipt for an unknown SKU, or the warehouses of one | 404 | `{"error": "unknown_sku"}` |

A receipt is checked in the order of this table. In a reservation, an unknown warehouse comes right after an unknown SKU.

### Example 1

<!-- case: v11 -->

The lamps all moved to `main`.

### Example 2

<!-- case: v12 -->

Four lamps arrive in `north`, and the product's total counts them.

## Constraints

- Postgres 17, through `DATABASE_URL`, with node-pg-migrate's plain SQL migrations. The baseline migration stays as it is.
- Bursts of up to 20 requests at once; a case has 10 s for all its requests.
- Every answer of a case that repeats must be right on every run: a race that loses one time in three still fails.
- Grading applies your migrations to a database that already holds hidden products, and to an empty one.

## Follow-ups

- Every reservation here waits on row locks. What would `SERIALIZABLE` isolation do instead, and what must the service then do with the transactions Postgres refuses?
- A sale on one product makes every checkout queue on its one row. How would you spread that hot row, and what would counting the stock then cost?
- Expired holds keep their rows forever. When would you delete them, and what must a cleanup job never race with?
- A payment service calls `DELETE` and then charges the card. What happens when the release succeeds and the charge fails, and what would you change so the order cannot end half done?
- The level 4 migration rewrites a table in one transaction, which locks it while it runs. On a table of fifty million rows, how would you split it so the shop keeps selling?
- A customer pays at the moment their hold expires. Who should win, and where in the code does that decision belong?

## Hints

### Hint 1

Start with one migration that adds a `reservations` table keyed by the order, and a table of its items. A primary key on the order id is already the rule "one reservation per order", and it holds when two requests arrive at once.

### Hint 2

`pool.connect()` gives you one connection to run `BEGIN`, your statements and `COMMIT` on. Statements through `pool.query` each take whichever connection is free, so they are not one transaction.

### Hint 3

`SELECT ... FROM products WHERE sku = $1 FOR UPDATE` inside a transaction makes every other transaction that locks the same row wait until you commit. Read what is available after taking the lock, not before.

### Hint 4

A release is one statement: `UPDATE ... SET status = 'released' WHERE order_id = $1 AND status = 'active'`, and `rowCount` says whether this request was the one that released it.

### Hint 5

If what is available is computed, stock minus active holds, an expired hold stops counting by itself: compare its expiry with `now()` where you count. Sort the items by SKU before locking them, and two orders can no longer wait on each other.

### Hint 6

For level 4, create the new table, copy into it with `INSERT ... SELECT` from `products`, and only then drop what you replaced. A new column on a table with rows needs a default, or the migration fails on the rows already there.
