# Loan Pipeline Service

A small service that tracks loan applications through a pipeline. It already works: it can list applications, read one and open a new one. You did not write it, so start by finding your way around.

## Contract

- `src/app.ts` exports the class `LoanApi` by name, and `new LoanApi()` takes no arguments. Keep the file and the export where they are: `cstudy submit` imports the class from there.
- `request(method, path, body)` returns `[status, json]`, both strings. Keep that shape.

Everything else is yours to change, move or add to.

## Layout

| Path | Holds |
|------|-------|
| `src/app.ts` | `LoanApi`: wires the store to the routes and turns a handler's answer into `[status, json]` |
| `src/http/router.ts` | The router: matches a method and a path to a handler, and parses path parameters and the query string |
| `src/http/json.ts` | `stableStringify`: JSON with object keys in sorted order |
| `src/routes/loans.ts` | The handlers for `/loans` |
| `src/routes/internal.ts` | The test seam that simulates a store outage |
| `src/data/loanStore.ts` | `LoanStore`: the in-memory table of loans |
| `src/data/seed.ts` | The rows the store starts with |
| `src/errors.ts` | `ApiError`: errors the API answers on purpose |
| `src/types.ts` | The data types |
| `tests/http.test.ts` | Tests of the router and of `stableStringify` |
| `tests/level-<n>.test.ts` | The examples of each open level, written by `cstudy` when the level opens; yours to edit, never rewritten |

## There is no real HTTP server

No dependencies are allowed, so `request` stands in for the network: the method and the path arrive as they would in an HTTP request line, the path with its query string, and the body as the raw text a client sent. Handlers return a status and a plain object.

`LoanApi.request` serializes every answer with `stableStringify`, so the order in which you build an object's keys never matters: an answer always has its keys sorted, and no whitespace.

## Running the tests

From this folder:

```sh
node --test
node --test tests/level-1.test.ts
```

From the workspace, `cstudy test loan-pipeline-service-typescript` runs the same tests. Node strips the types without checking them; `../../typescript/node_modules/.bin/tsc` here, or `cstudy test --typecheck`, type-checks the project.

Use erasable syntax only (no `enum`, no `namespace`, no constructor parameter properties), and import your own files with their `.ts` extension. Nothing is installed here: the project uses the workspace's Node and TypeScript.

## Grading

Your tests are feedback only. `cstudy submit loan-pipeline-service-typescript` grades every case of the open levels, hidden ones included, and opens the next level when they all pass. Each submission grades the earlier levels again.

A failure report cuts long values at 200 characters, which can hide the part that differs. `cstudy submit loan-pipeline-service-typescript --json` prints them whole.
