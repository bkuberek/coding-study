# Supplier Records

A small service that keeps the company's supplier records. Several people edit them, and at the moment the last save simply wins. It works today: it lists suppliers, reads one, creates one and saves one.

The code separates what changes state from what reads it: one file per command, one file per query, and the plumbing in `kernel/`.

## Contract

- `src/api.ts` exports the class `SupplierApi` by name, and `new SupplierApi()` takes no arguments. Keep the file and the export where they are: `cstudy submit` imports the class from there.
- `request(method, path, body)` returns `[status, json]`, both strings. Keep that shape.

Everything else is yours to change, move or add to.

## Layout

| Path | Holds |
|------|-------|
| `src/api.ts` | `SupplierApi`: the route table, and the one place that turns every outcome into text |
| `src/commands/` | One file per request that changes something |
| `src/queries/` | One file per request that only reads |
| `src/model/supplier.ts` | The fields of a supplier and the rules for each |
| `src/model/supplierStore.ts` | The suppliers, in memory, and the two seeded ones |
| `src/kernel/router.ts` | How a request finds its route |
| `src/kernel/body.ts` | Reading a JSON object from a request body |
| `src/kernel/errors.ts` | `ApiError`: failures the API answers on purpose |
| `src/kernel/json.ts` | `canonicalJson`: JSON with object keys in sorted order |
| `tests/kernel.test.ts` | Tests of the plumbing and of the field rules |
| `tests/level-<n>.test.ts` | The examples of each open level, written by `cstudy` when the level opens; yours to edit, never rewritten |

A new request gets a file of its own under `commands/` or `queries/`, and a line in the table in `src/api.ts`.

## There is no real HTTP server

No dependencies are allowed, so `request` stands in for the network. `method` is in upper case, `path` has no query string, and `body` is the raw text a client sent, `""` for none. `SupplierApi.request` serializes every answer with `canonicalJson`, so the order in which you build an object's keys never matters.

## Running the tests

From this folder:

```sh
node --test
node --test tests/level-1.test.ts
```

From the workspace, `cstudy test supplier-records-locking-typescript` runs the same tests. Node strips the types without checking them; `../../typescript/node_modules/.bin/tsc` here, or `cstudy test --typecheck`, type-checks the project.

Use erasable syntax only (no `enum`, no `namespace`, no constructor parameter properties), and import your own files with their `.ts` extension. Nothing is installed here: the project uses the workspace's Node and TypeScript.

## Grading

Your tests are feedback only. `cstudy submit supplier-records-locking-typescript` grades every case of the open levels, hidden ones included, and opens the next level when they all pass. Each submission grades the earlier levels again.

A failure report cuts long values at 200 characters, which can hide the part that differs. `cstudy submit supplier-records-locking-typescript --json` prints them whole.
