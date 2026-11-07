# Idempotent Document Consumer

A worker that takes scanned documents off a queue, extracts them and records the result. It works on a good day. The queue delivers at least once, so good days are not what it will get.

## Contract

- `src/consumer.ts` exports the class `DocumentConsumer` by name, and `new DocumentConsumer()` takes no arguments. Keep the file and the export where they are: `cstudy submit` imports the class from there.
- Each level names the methods it adds, with their parameters and return types. Keep those names and signatures.

Everything else is yours to change, move or add to.

## Layout

| Path | Holds |
|------|-------|
| `src/consumer.ts` | `DocumentConsumer`: the process, which builds the rest and answers the broker |
| `src/worker/delivery.ts` | `parseDelivery`: delivery text to a typed `Delivery`, or `MalformedDelivery` |
| `src/worker/handler.ts` | `DeliveryHandler`: what happens to one delivery |
| `src/extraction/extractor.ts` | `Extractor`: the paid step that reads a scan |
| `src/storage/database.ts` | `Database`: the tables and `transaction` |
| `src/storage/documentIndex.ts`, `src/storage/ledger.ts` | One table each |
| `src/runtime/faults.ts` | `Faults`: switches that tests use to make things fail. A production build would not have them |
| `src/json.ts` | `canonicalJson`: JSON with object keys in sorted order |
| `tests/storage.test.ts` | Tests of the pieces above |
| `tests/level-<n>.test.ts` | The examples of each open level, written by `cstudy` when the level opens; yours to edit, never rewritten |

## There is no real queue

No dependencies are allowed, so a test plays the broker: it calls `deliver` with the text of a delivery, and your answer is what the broker would act on. The database is an object in memory, and it stands for one on another machine, which is why it outlives the worker.

## Running the tests

From this folder:

```sh
node --test
node --test tests/level-1.test.ts
```

From the workspace, `cstudy test idempotent-document-consumer-typescript` runs the same tests. Node strips the types without checking them; `../../typescript/node_modules/.bin/tsc` here, or `cstudy test --typecheck`, type-checks the project.

Use erasable syntax only (no `enum`, no `namespace`, no constructor parameter properties), and import your own files with their `.ts` extension. Nothing is installed here: the project uses the workspace's Node and TypeScript.

## Grading

Your tests are feedback only. `cstudy submit idempotent-document-consumer-typescript` grades every case of the open levels, hidden ones included, and opens the next level when they all pass. Each submission grades the earlier levels again.
