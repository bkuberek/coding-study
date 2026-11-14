# Loan Pipeline Service (TypeScript)

## Statement

You join a team that owns a small service tracking loan applications through a pipeline. It runs today: it lists applications, reads one and opens a new one. You did not write it, and nobody is free to walk you through it. Each level asks for one more change of the kind such a service gets every week, and you make each change in the code you already have.

All the people, amounts and rules here are invented.

The service has no network layer. A test plays the client by calling `request`, which takes what an HTTP request would carry and returns a status and a JSON body.

## Input

- `new LoanApi()`: a service holding four seeded loans, `L-1001` to `L-1004`. Each test gets a new one.
- `method`: the HTTP method, in upper case.
- `path`: the path with its query string, as a client sends it: `/loans?stage=review`.
- `body`: the raw request text, `""` when there is none. It may be anything a client can send, broken JSON included.

## Output

`request` returns `[status, json]`, two strings: the status code as text, and the body as JSON text.

The keys of every object in `json` are in sorted order, with no whitespace, because `request` serializes every answer through `stableStringify`. So the examples below show keys in sorted order, and the order in which your code builds an object does not matter.

A failure has this shape:

```json
{"error":{"code":"not_found","message":"No loan with id L-9999"}}
```

## Project

`cstudy start` copies the service into `projects/loan-pipeline-service-typescript/`:

- `src/app.ts`: the class `LoanApi`, exported by name, which must stay there.
- `src/http/`: the router and `stableStringify`.
- `src/routes/`: the handlers, one file per resource.
- `src/data/`: the in-memory store and its seed rows.
- `src/errors.ts` and `src/types.ts`: the error class and the data types.
- `tests/http.test.ts`: tests of the plumbing, and `tests/level-<n>.test.ts`: the examples of each open level as `node:test` tests, written when the level opens and never rewritten.
- `README.md`, `package.json` and `tsconfig.json`.

The starter already answers these:

| Request | Answer |
|---------|--------|
| `GET /loans` | 200, `{"items":[...],"page":1,"pageSize":20,"total":4}`, in creation order |
| `GET /loans/:id` | 200 with the loan, or 404 `not_found` with the message `No loan with id <id>` |
| `POST /loans` with `applicant`, `amountCents` and `appliedOn` | 201 with the new loan: the next id (`L-1005` first) and the stage `submitted` |
| A path no route has | 404 `route_not_found` with the message `No route for <METHOD> <path>` |
| A route's path with another method | 405 `method_not_allowed` with the message `Method <METHOD> not allowed on <path>` |

`POST /internal/store-outage` with `{"reason":"..."}` makes every store call throw `new Error(reason)` until `DELETE /internal/store-outage`, which lets a test act out a database outage. Both answer 200.

`cstudy test loan-pipeline-service-typescript` runs your tests, and so does `node --test` in the project folder; either run is feedback only, and `cstudy test --typecheck` also type-checks the project. `cstudy submit loan-pipeline-service-typescript` grades every case of the open levels, hidden ones included, and opens the next level when they all pass. Each submission grades the earlier levels again, so a later change must keep their rules. Node runs the files by stripping their types, so write no `enum`, no `namespace` and no constructor parameter properties, and import your own files with their `.ts` extension.

## Level 1: New fields end to end

Underwriting wants three more facts on every loan. Add them everywhere a loan goes: `GET /loans`, `GET /loans/:id` and `POST /loans`.

| Field | Type | When a client leaves it out or sends `null` |
|-------|------|---------------------------------------------|
| `termMonths` | whole number | `36` |
| `purpose` | text | `"unspecified"` |
| `coApplicant` | text or `null` | `null` |

The four seeded loans predate these fields, so they take the same defaults. A loan always has all three keys, `coApplicant` included.

### Example 1

<!-- case: ex1 -->

The seeded loan `L-1002` reads back with its defaults. A new loan keeps the values its client sent, in the answer to `POST` and on a later `GET`.

### Example 2

<!-- case: ex2 -->

A client that sends none of the new fields gets the defaults, and the new loan comes last in the list.

## Level 2: Validation and safe errors

Clients send bad requests, and the store sometimes fails. Neither may look like anything but a clear answer.

**Broken bodies.** On `POST /loans`, a body that is not valid JSON, or valid JSON that is not an object (`null`, `[]`, `42`), answers 400:

```json
{"error":{"code":"invalid_json","message":"Request body must be a JSON object"}}
```

**Field errors.** A body with bad fields answers 400, listing every bad field, in the order of this table:

```json
{"error":{"code":"validation_failed","fields":[{"field":"amountCents","message":"must be a whole number from 1 to 100000000"}],"message":"Request validation failed"}}
```

| Field | Required | Valid values | Message |
|-------|----------|--------------|---------|
| `applicant` | yes | text that is not blank | `must be a non-empty string` |
| `amountCents` | yes | a JSON number, whole, from 1 to 100000000 | `must be a whole number from 1 to 100000000` |
| `appliedOn` | yes | text `YYYY-MM-DD` naming a day that exists | `must be a real date as YYYY-MM-DD` |
| `termMonths` | no | a JSON number, whole, from 6 to 360 | `must be a whole number from 6 to 360` |
| `purpose` | no | `auto`, `business`, `education`, `home` or `unspecified` | `must be one of auto, business, education, home, unspecified` |
| `coApplicant` | no | `null`, or text that is not blank | `must be a non-empty string or null` |

`applicant` and `coApplicant` are stored without their surrounding spaces. Any other key in the body is ignored and never stored. A client cannot choose a loan's `id` or `stage`. A refused request creates nothing and uses up no id.

**Unexpected errors.** Any error that is not an answer on purpose, a store outage for one, answers 500 with exactly this body, whatever the error said, and the service keeps working once the cause goes away:

```json
{"error":{"code":"internal_error","message":"Internal server error"}}
```

### Example 1

<!-- case: ex3 -->

Both bad fields are listed, in table order, and the refused request created nothing: `L-1005` does not exist.

### Example 2

<!-- case: ex4 -->

Broken JSON is the client's fault, so it is a 400. During the outage the same service answers 500, and the outage's reason text stays out of the answer. Once the outage ends, reads work again.

## Level 3: Filter search and sort

`GET /loans` takes these query parameters, in any combination. Filters narrow the list, `total` counts the loans that match them, and unknown parameters are ignored.

| Parameter | Meaning | Valid values | Message when invalid |
|-----------|---------|--------------|----------------------|
| `stage` | Only loans in this stage | `approved`, `declined`, `funded`, `review`, `submitted`, `withdrawn` | `must be one of approved, declined, funded, review, submitted, withdrawn` |
| `q` | Only loans whose `applicant` contains this text, ignoring case | Any text; empty means no filter | |
| `minAmountCents` | Only loans with at least this amount | Digits only | `must be a whole number` |
| `maxAmountCents` | Only loans with at most this amount | Digits only | `must be a whole number` |
| `sort` | The key to sort by; by default `id` | `amountCents`, `applicant`, `appliedOn`, `id`, `termMonths` | `must be one of amountCents, applicant, appliedOn, id, termMonths` |
| `order` | The direction; by default `asc` | `asc`, `desc` | `must be asc or desc` |

Amounts and terms sort as numbers, the others as text compared with `<`. Loans with equal values for the sort key always follow each other in `id` order, ascending, whichever the direction. Any invalid value answers 400, listing every bad parameter in the order of this table:

```json
{"error":{"code":"invalid_query","fields":[{"field":"order","message":"must be asc or desc"}],"message":"Request query is invalid"}}
```

### Example 1

<!-- case: ex5 -->

`q` ignores case, and `total` counts what the filters leave: one loan for each of the first two requests, and none when two filters exclude each other.

### Example 2

<!-- case: ex6 -->

Sorted by amount, descending: 9900000 comes first, then 1250000, 480000 and 75000.

### Example 3

<!-- case: ex7 -->

`plaything` is not a sort key and `open` is not a stage. The answer names both, `stage` first, and no list is returned.

## Level 4: Pagination

The list grows, so `GET /loans` now answers one page at a time. A request with neither parameter gets the first 20 matching loans.

| Parameter | Meaning | Rules |
|-----------|---------|-------|
| `page` | The page to return, counted from 1 | Default 1 |
| `pageSize` | How many loans a page holds | Default 20. A value above 100 is not an error: it counts as 100, and the answer's `pageSize` says 100 |

A value that is not digits forming a whole number of at least 1 is an invalid query, with the message `must be a whole number of at least 1`; `page` and `pageSize` come last in the `fields` order, in that order. The answer's `page` and `pageSize` are the numbers used, and `total` still counts every loan that matches the filters, on any page. A page past the end is not an error: it has no items, and the same `total`.

### Example 1

<!-- case: ex8 -->

The second page of two holds the third and the fourth loan, and `total` is still 4. `page` and `pageSize` come back as numbers.

### Example 2

<!-- case: ex9 -->

A `pageSize` of 500 counts as 100, and a `page` of 0 is refused.

## Level 5: Stage transitions

Loans move through the pipeline by `POST /loans/:id/transition` with a body such as `{"to":"review"}`. The moves allowed are exactly these:

| From | To |
|------|----|
| `submitted` | `review`, `withdrawn` |
| `review` | `approved`, `declined`, `withdrawn` |
| `approved` | `funded`, `withdrawn` |
| `funded`, `declined`, `withdrawn` | Nothing: these stages are terminal |

A request is checked in this order, and the first problem found is the answer:

| Check | Answer |
|-------|--------|
| The loan exists | 404 `not_found`, the message as for `GET /loans/:id`, whatever the body says |
| The body is a JSON object | 400 `invalid_json`, as in level 2 |
| `to` is a known stage | 400 `validation_failed` for the field `to`, with the message `must be one of approved, declined, funded, review, submitted, withdrawn` |
| The move is allowed | 422 `illegal_transition`, with the message `Cannot move a loan from <from> to <to>` |

A move that is allowed answers 200 with the updated loan. A refused move changes nothing.

### Example 1

<!-- case: ex10 -->

`submitted` may go to `review`, but `review` may not jump to `funded`: that is a 422, and the loan stays in `review`.

### Example 2

<!-- case: ex11 -->

Three different mistakes get three different answers: no such loan, a body that is not JSON, and a stage that does not exist.

## Level 6: Conditions

Underwriters attach conditions to a loan, such as "proof of income", and the loan cannot go ahead until they are met.

| Request | Answer |
|---------|--------|
| `POST /loans/:id/conditions` with `{"text":"..."}` | 201 with the new condition: `{"id":"C-1","loanId":"L-1001","status":"open","text":"..."}`. Ids number the conditions of the whole service, from `C-1`. The text is stored without its surrounding spaces |
| `GET /loans/:id/conditions` | 200, `{"items":[...],"total":n}`, the loan's conditions in creation order, cleared ones included |
| `POST /loans/:id/conditions/:conditionId/clear` | 200 with the condition, now `cleared`. Clearing a cleared condition answers the same |

An unknown loan is a 404, as in level 5, on all three. A condition id that is unknown, or that belongs to another loan, is a 404 `not_found` with the message `No condition <conditionId> on loan <id>`.

`POST /loans/:id/conditions` checks, in this order: the loan exists; the body is a JSON object; `text` is text that is not blank, or 400 `validation_failed` for the field `text` with the message `must be a non-empty string`; and the loan's stage is not terminal, or 422 `loan_closed` with the message `Loan <id> is closed`.

A move to `approved` or `funded` that level 5 allows is now refused while the loan has an open condition. That check comes last, and it answers 409, listing the open conditions in creation order. A move to `declined` or `withdrawn` never waits for conditions.

```json
{"error":{"code":"conditions_open","message":"Loan L-1001 has open conditions","openConditionIds":["C-1"]}}
```

### Example 1

<!-- case: ex12 -->

A condition starts `open` and appears under its loan. Clearing it answers the condition again, now `cleared`, and it stays in the list.

### Example 2

<!-- case: ex13 -->

`L-1001` cannot be approved while `C-1` is open. Once `C-1` is cleared, the same move goes through.

## Constraints

- At most 1000 calls per test.
- Applicant names are short ASCII text; amounts and terms are as each level states.
- Nothing reads a clock: dates arrive in request bodies.

## Follow-ups

- Two people change the same loan at the same moment. What guards that in a real database, and where would the guard live?
- How would you move this service from an in-memory table to SQL without touching the routes? Which of your functions would become a query?
- A list read one page at a time repeats or skips rows when rows arrive between two requests. What would you hand the client instead of a page number?

## Hints

### Hint 1

Before you change anything, follow one request by hand from `LoanApi.request` to the store and back. Then ask which of those files each new requirement touches.

### Hint 2

Everything from outside arrives as text, and `Number` and `<` quietly accept more than you think. Turn each value into a checked value once, at the edge of the service, and let the rest of the code work on real numbers.

### Hint 3

When a request can fail in several ways, write down the order of the checks first, and make every check happen before anything changes.

### Hint 4

Rules about what may follow what read and test better as a table than as a chain of `if`s, and an empty row in the table says "nothing follows this" without another rule.
