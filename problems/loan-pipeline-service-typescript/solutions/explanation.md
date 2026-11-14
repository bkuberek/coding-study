# Loan Pipeline Service (TypeScript): Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | O(n log n) per list request; O(n) per other request | O(n + c) | default answer; each level adds one file or one narrow change to the layers already there |

Here `n` is the number of loans and `c` the number of conditions.

## How the project grows level by level

| Level | New requirement | What the code adds |
|-------|-----------------|--------------------|
| 1 | Three more fields on every loan | The fields in `src/types.ts`, the store's `insert`, the create handler and the seed rows, with `LOAN_DEFAULTS` in one place |
| 2 | Validation and safe errors | `src/http/body.ts`, `src/validation/loans.ts`, more constructors in `src/errors.ts`, and the catch-all in `LoanApi.#respond` |
| 3 | Filter, search and sort | `src/validation/listQuery.ts` and `src/data/listing.ts`; the list handler shrinks to two lines |
| 4 | Pagination | Two more parameters in `parseListQuery` and one `slice` in `selectPage`: the response shape was already there |
| 5 | Stage transitions | `src/domain/stages.ts`, the table of moves, and one route |
| 6 | Conditions | `src/data/conditionStore.ts`, `src/routes/conditions.ts`, and one check in the transition route |

## Approach: reference (Layered service with a pure listing pipeline and a stage table)

### Intuition

The skill here is not the code in any one level. It is finding the place a change belongs, in a service you did not write, and keeping the rule in one place when you put it there. A request crosses four layers, and each answers one question: `http/` asks what was sent, `validation/` asks whether it makes sense, `routes/` asks what to do, and `data/` asks what is stored. Most mistakes in this problem come from answering a question in the wrong layer: a query value compared as text inside the store, a transition rule spelled out in a handler, an error message built where the error was caught.

### Algorithm

1. Level 1: add the fields to the types and let the compiler list what is now incomplete (`cstudy test --typecheck` shows the seed rows and the store). Keep the defaults in one object, and spread them into the old rows, as a migration's `DEFAULT` would.
2. Level 2: `readJsonObject` turns the body into an object or a 400. `parseNewLoan` runs every check, collects the failures, and throws them together, so one answer lists every problem. `LoanApi.#respond` answers an `ApiError` as it is, and turns anything else into the one generic 500.
3. Level 3: `parseListQuery` turns strings into a typed `ListQuery`, collecting failures. `selectPage` filters, then sorts a copy by the key with the id as the tie-break.
4. Level 4: the same parser reads `page` and `pageSize`, and `selectPage` takes `total` from the matches before it cuts the page.
5. Level 5: the route finds the loan (404), parses the move (400), asks the table (422), then writes.
6. Level 6: the same route asks one question more before the write (409), and the condition routes all begin by finding the parent.

### Design

| File | Responsible for |
|------|-----------------|
| `src/app.ts` | `LoanApi`: wiring, and the only `try`/`catch`, where every failure becomes an answer |
| `src/http/router.ts`, `src/http/json.ts` | Matching routes and serializing answers: know nothing about loans. Unchanged from the starter |
| `src/http/body.ts` | Text to JSON object, or a 400 |
| `src/validation/loans.ts`, `src/validation/listQuery.ts` | Untrusted input to typed values, reporting every problem at once |
| `src/domain/stages.ts` | The table of moves, and the two rules read from it |
| `src/domain/loanDefaults.ts` | The defaults, shared by the validator and the seed rows |
| `src/data/loanStore.ts`, `src/data/conditionStore.ts`, `src/data/seed.ts` | The tables. A real service would swap these for queries and keep everything above |
| `src/data/listing.ts` | Filter, sort and page as one pure function, testable without a request |
| `src/routes/*.ts` | The order of the checks for each request, and nothing else |
| `src/errors.ts` | Each error the API answers on purpose, with its status and its code |
| `tests/listing.test.ts`, `tests/stages.test.ts` | The pipeline's order and the whole move table, tested without going through `request` |

**Why JSON comes out with sorted keys.** The tests compare text, and two correct solutions must not differ because one built its object in another order. `LoanApi.request` is the one place where an answer becomes text, so that is where `stableStringify` runs, and no handler has to think about it. In production you would not normally sort keys, because clients must not care. But the idea carries over: serialize at one choke point, so error shapes, redaction and logging have one home.

**Why a table for the state machine.** "From `review` you can go to `approved`, `declined` or `withdrawn`" is data. As data it can be read by a person who does not read code, tested exhaustively in six nested lines, and printed. As a chain of `if`s it tends to grow a branch that forgets the terminal stages.

**What a senior engineer says out loud.** Roughly, level by level:

- Level 1: "Existing rows are the first client of a new field. What do they read as, and does that default mean 'unknown' or does it claim something? I'd rather store `unspecified` than pretend."
- Level 2: "I report all the bad fields at once, so a form can show them together. The 500 says nothing, because its message is written for me, not the caller: hostnames and table names are how a small leak starts. And I log it, with an id I could give the caller."
- Level 3: "`sort` is an allowlist because in SQL it would go into `ORDER BY`, which can't be a bound parameter. And the tie-break is on purpose: without a unique last key, the order between pages isn't defined."
- Level 4: "Cap the page size silently or refuse it? I cap it and say so in the response, so an old client keeps working. The cap protects the database."
- Level 5: "404, 400 and 422 tell the client three different things: this isn't there, I can't read you, and I read you but the answer is no. A client can retry none of them unchanged, but only the last one is about the business rule."
- Level 6: "A condition has to be looked up through its loan, or anyone who can guess `C-7` can clear another loan's condition. That is the shape of most authorization bugs."

**What they would do next in production.**

- Put a `version` on the loan, or use `UPDATE ... WHERE stage = :expected`, because the read and the write in the transition route are not atomic once two processes share a database.
- Record each transition as a row (who, when, from, to). For a loan, the history is usually the point, and it makes the current stage a value you can check.
- Use a cursor instead of `page` for large lists, because offset paging gets slower with depth and repeats rows when new ones arrive.
- Add a request id to every log line and to the 500's body, so a support ticket can find the failure.
- Replace `/internal/store-outage`: it exists because these tests can only talk through `request`. Normally you would inject a failing store in the test's setup and expose no such route.

### Correctness

Every request ends in one of two ways: a handler returns, or something throws. `LoanApi.#respond` is the only `catch`, so every throw becomes an answer, and only an `ApiError` chooses its own body. So no internal message can reach a client, and the 500 body is one constant.

`parseNewLoan` throws before anything is written, and `LoanStore.insert` is the only place that takes an id, after its availability check. So a refused request and a failed write use up no id and create nothing. The stored loan is built field by field, so a key the client added cannot reach it.

`selectPage` works on the array `filter` returns and sorts it with `toSorted`, so the table keeps its creation order. The comparator is a total order on loans, because ids are unique, so the sorted order is the same on every request and pages partition the matches: no row repeats and none is lost. `total` is read from the matches before the page is cut.

The transition route writes only after every check has passed, so a refused move changes nothing. `canMove` reads the table in `src/domain/stages.ts`, whose terminal rows are empty, so no move leaves them. The condition check comes after `canMove`, so a move that is not allowed is a 422 whatever its conditions, and `needsClearedConditions` is false for `declined` and `withdrawn`, so these never wait.

### Complexity

- Time: O(n log n) per list request; O(n) per other request — the list filters every loan and sorts the matches; reading a loan by id scans the table, and listing a loan's conditions scans the conditions. A real database would index both.
- Space: O(n + c) — one record per loan and per condition. A list request allocates a filtered copy.

### Trade-offs

- Validating by hand, as here, against a schema library: a schema library gives you all of this for less code and better messages, and you would normally use one. Writing it once by hand shows what such a library does, and it is what the no-dependency rule leaves.
- Filtering in the route handler is shorter at level 3, but `selectPage` can be tested with no request at all, and it is one function to replace with a query.
- Reading `stage` in each handler and comparing it in place would need no table, until a third handler needs the same rule.
- 422 for an illegal move and 409 for open conditions are a choice, and teams argue about it. Here 422 says "this request can never work from this state as asked", and 409 says "your request is fine but the state is in the way, and it can change". What matters is that the contract states it and the client can tell the two apart.

### Pitfalls and edge cases

Each wrong approach below was run against the hidden cases named with it, and each fails them.

- **Sorting numbers as strings.** `String(a[key]).localeCompare(String(b[key]))`, or a `.sort()` with no comparator, puts 1250000 before 75000. Caught by `h16`, and for terms by `h22`.
- **`order=desc` by reversing an ascending sort.** It also reverses the ties, so `L-1006` comes before `L-1005`. Caught by `h17`, and across pages by `h32`.
- **Sorting the table in place.** `store.list().sort(...)` sorts the array inside the store, so the next plain `GET /loans` comes back in the wrong order. Caught by `h23`.
- **`key in loan` as the allowlist.** `"constructor" in loan` is true, because `in` walks the prototype chain. Caught by `h20`, and for stages by `h39`.
- **Comparing query values as text.** `"75000" >= "100000"` is true. Caught by `h18`.
- **`Number(value)` without a format check.** `Number("")` is 0 and `Number("1e3")` is 1000, so bad queries pass. Caught by `h19` and `h31`.
- **Counting totals before filtering, or after paging.** `store.count()` ignores the filters, and `items.length` stops at the page. Caught by `h26`.
- **Echoing the query's text.** `page: query.get("page")` answers `"page":"2"`. Caught by `ex8`.
- **Cutting the page at the requested size while answering the capped one.** Caught by `h29`, which has more than 100 loans.
- **Stopping at the first bad field.** Caught by `h6` and `h10`.
- **`||` for defaults.** `input.termMonths || 36` turns a `termMonths` of 0 into a valid 36 instead of a refusal. Caught by `h10`.
- **Spreading the body into the record.** `{ ...input, id, stage: "submitted" }` stores whatever else the client sent. Caught by `h11`.
- **Trusting `new Date` to reject a bad day.** On V8, `new Date("2026-02-30")` is a valid 2 March. Read the date back and compare. Caught by `h9`.
- **Sending `error.message` in the 500.** Caught by `ex4` and `h14`.
- **A catch-all that also swallows `ApiError`.** Every 404 becomes a 500. Caught by `h15`.
- **A transition table that lets a terminal stage move, or leaves `approved` free to go to `declined`.** Caught by `h35` and `h36`.
- **Writing the stage before checking conditions.** The 409 leaves the loan moved. Caught by `h46`.
- **Blocking every move on open conditions.** A loan with an open condition could then never be declined. Caught by `h44`.
- **Checking conditions before legality.** A `submitted` loan with a condition then gets a 409 for a move that can never work. Caught by `h45`.
- **Finding a condition by its id alone.** One loan's URL can then clear another loan's condition. Caught by `h43`.
- **Reading a body before checking the parent.** Caught by `h38` and `h42`.
- Project traps: `src/app.ts` must export `LoanApi` by name; local imports need their `.ts` extension; `enum`, `namespace` and constructor parameter properties make Node refuse the file before any test runs.
