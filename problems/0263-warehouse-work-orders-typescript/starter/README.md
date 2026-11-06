# Warehouse Work Orders

A small service that tracks maintenance work across a company's warehouse sites. It works today: it lists sites and work orders, reads one, and opens a new one, validating what it is sent. The code is organized by feature, so everything about work orders sits in one folder.

## Contract

- `src/server.ts` exports the class `WorkOrderApi` by name, and `new WorkOrderApi()` takes no arguments. Keep the file and the export where they are: `cstudy submit` imports the class from there.
- `request(method, path, headers, body)` returns `[status, json]`, both strings. Keep that shape.

Everything else is yours to change, move or add to.

## Layout

| Path | Holds |
|------|-------|
| `src/server.ts` | `WorkOrderApi`: builds the features and turns an answer into `[status, json]` |
| `src/shared/routing.ts` | The route table and how a request finds its route |
| `src/shared/body.ts` | Reading a JSON object from a request body |
| `src/shared/json.ts` | `canonicalJson`: JSON with object keys in sorted order |
| `src/shared/problems.ts` | `HttpProblem`: failures the API answers on purpose |
| `src/sites/` | The site directory and `GET /sites` |
| `src/workorders/` | The work order's model, store, validation and routes |
| `tests/routing.test.ts` | Tests of the routing |
| `tests/level-<n>.test.ts` | The examples of each open level, written by `cstudy` when the level opens; yours to edit, never rewritten |

A new feature gets a folder of its own under `src/`. Its routes join the table in `src/server.ts`.

## There is no real HTTP server

No dependencies are allowed, so `request` stands in for the network. The method and the path arrive as they would in an HTTP request line, the path with its query string. `headers` is a list of `"Name: value"` strings, and the body is the raw text a client sent. Header names reach a handler in lower case, as they do in Node's own HTTP server, so a handler reads `request.headers.get("x-request-id")`.

`WorkOrderApi.request` serializes every answer with `canonicalJson`, so the order in which you build an object's keys never matters.

## Running the tests

From this folder:

```sh
node --test
node --test tests/level-1.test.ts
```

From the workspace, `cstudy test warehouse-work-orders-typescript` runs the same tests. Node strips the types without checking them; `../../typescript/node_modules/.bin/tsc` here, or `cstudy test --typecheck`, type-checks the project.

Use erasable syntax only (no `enum`, no `namespace`, no constructor parameter properties), and import your own files with their `.ts` extension. Nothing is installed here: the project uses the workspace's Node and TypeScript.

## Grading

Your tests are feedback only. `cstudy submit warehouse-work-orders-typescript` grades every case of the open levels, hidden ones included, and opens the next level when they all pass. Each submission grades the earlier levels again.

A failure report cuts long values at 200 characters, which can hide the part that differs. `cstudy submit warehouse-work-orders-typescript --json` prints them whole.
