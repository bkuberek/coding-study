# Warehouse Work Orders (TypeScript)

## Statement

A company runs maintenance across three warehouse sites, and a small service tracks each job as a work order. It runs today: it lists sites and work orders, reads one order, and opens a new one with validation. You are new to its code. Each level is a change the team has been putting off, the kind that sounds small and has a trap in it.

The sites, people, rates and rules here are invented.

The service has no network layer. A test plays the client by calling `request`, which takes what an HTTP request would carry and returns a status and a JSON body.

## Input

- `new WorkOrderApi()`: a service holding three sites and three work orders, `WO-101` to `WO-103`. Each test gets a new one.
- `method`: the HTTP method, in upper case.
- `path`: the path with its query string.
- `headers`: the request's headers as `"Name: value"` strings, `[]` for none. Header names may arrive in any case.
- `body`: the raw request text, `""` when there is none.

## Output

`request` returns `[status, json]`, two strings: the status code as text, and the body as JSON text. Every object in `json` has its keys in sorted order, with no whitespace, because `request` serializes every answer through `canonicalJson`, so the order in which your code builds an object does not matter.

A failure has this shape; a failure about specific fields adds a `fields` list, one `{"field":...,"message":...}` per bad field:

```json
{"error":{"code":"not_found","message":"No work order WO-999"}}
```

## Project

`cstudy start` copies the service into `projects/warehouse-work-orders-typescript/`. The code is organized by feature:

- `src/server.ts`: the class `WorkOrderApi`, exported by name, which must stay there.
- `src/shared/`: routing, reading a body, `canonicalJson` and the `HttpProblem` error class.
- `src/sites/`: the site directory and its route.
- `src/workorders/`: the model, the store, validation and routes.
- `tests/routing.test.ts`: tests of the routing, and `tests/level-<n>.test.ts`: the examples of each open level as `node:test` tests, written when the level opens and never rewritten.
- `README.md`, `package.json` and `tsconfig.json`.

The starter already answers these:

| Request | Answer |
|---------|--------|
| `GET /sites` | 200, `{"items":[...]}`, each site with `id`, `name`, `laborRateCentsPerHour` and `partsMarkupBasisPoints` |
| `GET /work-orders` | 200, `{"items":[...],"total":3}`, in creation order |
| `GET /work-orders/:id` | 200 with the work order, or 404 `not_found` with the message `No work order <id>` |
| `POST /work-orders` | 201 with the new work order: the next id (`WO-104` first) and `version` 1. A body that is not a JSON object is 400 `invalid_body`; bad fields are 400 `validation_failed` |
| A path no route has | 404 `route_not_found` |
| A route's path with another method | 405 `method_not_allowed` |

A work order has `id`, `siteId`, `title`, `priority` (`low`, `normal` or `high`, by default `normal`), `assignee` (text or `null`, by default `null`), `laborMinutes` (a whole number, by default 0) and `version`. Read `src/workorders/validate.ts` for the rules of a new one, which you will not need to change.

`cstudy test warehouse-work-orders-typescript` runs your tests, and so does `node --test` in the project folder; either run is feedback only, and `cstudy test --typecheck` also type-checks the project. `cstudy submit warehouse-work-orders-typescript` grades every case of the open levels, hidden ones included, and opens the next level when they all pass. Each submission grades the earlier levels again, so a later change must keep their rules. Node runs the files by stripping their types, so write no `enum`, no `namespace` and no constructor parameter properties, and import your own files with their `.ts` extension.

## Level 1: Idempotent create

A scanner on a loading dock retries when the network drops, and sometimes the first try had worked, so one job becomes two work orders. Clients will now send an `Idempotency-Key` header on `POST /work-orders`, naming the attempt. Without the header, nothing changes.

A request with the header is handled in this order:

| Step | Answer |
|------|--------|
| The key is blank | 400 `validation_failed` for the field `Idempotency-Key`, with the message `must not be blank` |
| The body is not a JSON object | 400 `invalid_body`, as today |
| The key was used for the same request | Exactly what the first request was told, the same status and the same body, whatever has happened to the order since. Nothing is created |
| The key was used for a different request | 422 `idempotency_conflict`, with the message `Idempotency key <key> was used with a different request`. Nothing is created |
| The fields are bad | 400 `validation_failed`, as today |
| Otherwise | 201, and the key now remembers this request and this answer |

Two requests are the same when their bodies hold the same JSON value, whatever the order of the keys or the spacing. A request that was refused is not remembered, so its key can be used again.

### Example 1

<!-- case: ex1 -->

The second `POST` repeats the key and the body, so it gets the first answer again, and there are four work orders, not five.

### Example 2

<!-- case: ex2 -->

The same key with another title is a client bug, not a retry. It is refused, and `WO-105` never exists.

## Level 2: Partial updates

Planners need to edit work orders. `PATCH /work-orders/:id` changes only what the body names:

| Field | Valid values | Message when invalid |
|-------|--------------|----------------------|
| `title` | Text that is not blank; stored without surrounding spaces | `must be a non-empty string` |
| `priority` | `low`, `normal`, `high` | `must be low, normal or high` |
| `assignee` | Text that is not blank, stored without surrounding spaces, or `null`, which clears the assignee | `must be a non-empty string or null` |
| `laborMinutes` | A JSON number, whole, from 0 to 100000 | `must be a whole number from 0 to 100000` |

A key that is missing leaves its field as it is. A `null` is a value, and only `assignee` accepts it. Any other key, `id` and `version` included, is refused with the message `cannot be changed`.

An unknown order is 404, whatever the body says. A body that is not a JSON object is 400 `invalid_body`. Bad fields answer 400 `validation_failed`, listing every bad field: those of the table first, in its order, then the other keys in sorted order. A refused request changes nothing at all.

A request that is accepted answers 200 with the work order. `version` goes up by 1 when a value actually changed; a request that changes no value, an empty object included, answers 200 and leaves `version` alone.

### Example 1

<!-- case: ex3 -->

`title` changes, `assignee` is cleared by the explicit `null`, and everything the body does not name stays. One request, so `version` goes up once.

### Example 2

<!-- case: ex4 -->

`urgent` is not a priority, so the whole request is refused: the title in the same body does not change either.

## Level 3: Cost in whole cents

Finance wants to know what each job costs. Add the parts used on a job, and a cost that is worked out when it is read, so it is never out of date.

`POST /work-orders/:id/parts` adds a line to the order and answers 201 with it:

```json
{"lineNumber":1,"quantity":3,"sku":"SHIM-8","unitCostCents":1200,"workOrderId":"WO-102"}
```

| Field | Valid values | Message when invalid |
|-------|--------------|----------------------|
| `sku` | Text that is not blank; stored without surrounding spaces | `must be a non-empty string` |
| `quantity` | A JSON number, whole, from 1 to 10000 | `must be a whole number from 1 to 10000` |
| `unitCostCents` | A JSON number, whole, from 0 to 1000000 | `must be a whole number from 0 to 1000000` |

An unknown order is 404. A body that is not a JSON object is 400 `invalid_body`. Bad fields answer 400 `validation_failed`, listing every bad field: those of the table first, in its order, then any other key in sorted order, with the message `is not a known field`. `lineNumber` counts the lines of that order from 1. Adding a line raises the order's `version` by 1; a refused request adds nothing and raises nothing.

`GET /work-orders/:id/cost` answers 200, or 404 for an unknown order, with the order's cost, using the rates of its site from `GET /sites`:

```json
{"laborCostCents":2993,"partsCostCents":0,"totalCostCents":2993,"workOrderId":"WO-103"}
```

- `laborCostCents` is `laborMinutes` times the site's `laborRateCentsPerHour`, divided by 60.
- `partsCostCents` is the sum over the order's lines of `quantity` times `unitCostCents`, plus the site's markup on that sum: `partsMarkupBasisPoints` is in hundredths of a percent, so 250 adds 2.5%.
- Each of the two is rounded once, to a whole cent, and an exact half rounds up. The markup is rounded on the order's sum, not line by line.
- `totalCostCents` is their sum.

### Example 1

<!-- case: ex5 -->

Three shims at 1200 cents make 3600. `WH-1` adds 2.5%, 90 cents, so the parts cost 3690. This order has no labor, and the new line has raised its `version` to 2.

### Example 2

<!-- case: ex6 -->

`WO-101` has 90 minutes at 4250 cents an hour, exactly 6375. `WO-103` has 45 minutes at 3990 cents an hour, exactly 2992.5, which rounds up to 2993.

## Level 4: Soft delete

Finance also needs old jobs kept, so a deleted work order must stay on record while the rest of the service forgets it.

`DELETE /work-orders/:id` answers 200 with `{"deleted":true,"id":"<id>"}`, and raises the order's `version` by 1.

From then on the order does not exist for `GET /work-orders/:id`, `PATCH`, `DELETE`, or the two routes of level 3: each answers the same 404 as for an order that never existed. `GET /work-orders` leaves it out of `items` and of `total`. Ids are never reused.

`GET /work-orders?includeDeleted=true` lists every order, deleted or not, and only in this form every row also has a boolean `deleted`. `includeDeleted=false` means the same as leaving it out. Any other value answers 400:

```json
{"error":{"code":"invalid_query","fields":[{"field":"includeDeleted","message":"must be true or false"}],"message":"Request query is invalid"}}
```

An idempotency key that created an order keeps answering as level 1 says, even after that order is deleted.

### Example 1

<!-- case: ex7 -->

Once `WO-102` is deleted, reading it is a 404 and the list shows two work orders.

### Example 2

<!-- case: ex8 -->

With `includeDeleted=true`, the row of `WO-102` comes back with `deleted` true and `version` 2, and the others with `deleted` false.

## Level 5: Optimistic locking

Two planners open the same order, and the second save silently undoes the first. Clients will now say which `version` they read, in an `If-Match` header, on `PATCH /work-orders/:id`, `DELETE /work-orders/:id` and `POST /work-orders/:id/parts`. Without the header, these work as before.

Those three requests now check, in this order:

| Check | Answer |
|-------|--------|
| The order exists | 404, as before |
| `If-Match` is digits only | 400 `validation_failed` for the field `If-Match`, with the message `must be a whole number` |
| `If-Match` equals the order's current `version` | 409, below, and nothing changes |
| The body and its fields, as their levels say | 400, and nothing changes |

```json
{"error":{"code":"version_conflict","currentVersion":2,"message":"Work order WO-101 is at version 2"}}
```

### Example 1

<!-- case: ex9 -->

Nobody has changed `WO-101`, so it is at version 1, and a client that says it read version 2 is refused. The order stays as it was.

### Example 2

<!-- case: ex10 -->

Two planners read version 1. The first saves and the order goes to version 2. The second's save is refused and told the current version, and it goes through once it says it has read that version.

## Level 6: Site cost report

`GET /reports/site-costs` answers 200 with what each site's live work orders cost:

```json
{"sites":[{"laborCostCents":6375,"orderCount":2,"partsCostCents":0,"siteId":"WH-1","siteName":"Harbor Annex","totalCostCents":6375}],"totals":{"laborCostCents":6375,"orderCount":2,"partsCostCents":0,"totalCostCents":6375}}
```

- `sites` has one row per site, in the order of `GET /sites`, every site included, with zeros when nothing counts for it.
- A row adds up the costs of its orders exactly as `GET /work-orders/:id/cost` gives them, so the report always equals the sum of what each order says. `totals` adds up the rows.
- Deleted orders do not count, and neither do their parts.
- `priority` in the query narrows the report to orders of that priority. Any value but `low`, `normal` and `high` answers 400 `invalid_query` for the field `priority`, with the message `must be low, normal or high`. Other parameters are ignored.

### Example 1

<!-- case: ex11 -->

The seeded orders: two at `WH-1`, whose labor comes to 6375, and one at `WH-2`, 2993. `WH-3` has none, and it is still in the report.

### Example 2

<!-- case: ex12 -->

`WO-102` gets a part worth 3690 cents and `WO-101` is deleted, so only `WO-102` counts at `WH-1`, with no labor.

## Constraints

- At most 1000 calls per test.
- Amounts stay far below `2^53` at every step of a calculation.
- Nothing reads a clock.

## Follow-ups

- Two copies of this service run behind a load balancer. What would have to move out of memory for each level to keep its promise, and which one is hardest?
- Should the remembered answer for a key live forever? What decides how long to keep it?
- Finance now wants the same report as of last month. What would you have to have stored?

## Hints

### Hint 1

Everything about a feature is in its folder, so first read how `src/workorders/routes.ts` handles a request from start to finish. A new feature gets a folder of its own, and its routes join the table in `src/server.ts`.

### Hint 2

`"key" in body` and `body.key` answer different questions. So do `value === null`, `value === undefined` and `!value`.

### Hint 3

A remembered answer should be a copy of what was said, not a reference to something that can still change.

### Hint 4

With money in whole cents, multiply before you divide, and leave rounding to one place, at the end. `Number` arithmetic stays exact as long as no step leaves the whole numbers.
