# Async Batch Importer

A small importer that writes a batch of SKUs to a store, then writes an audit entry. It reports that it has finished long before it has. Find out why, and fix it.

## Contract

- `src/importer.ts` exports the class `BatchImporter` by name, and `new BatchImporter()` takes no arguments. Keep the file and the export where they are: `cstudy submit` imports the class from there.
- Each level names the methods it adds, with their parameters and return types; `importAll` returns a `Promise`. Keep those names and signatures.

## Layout

| Path | Holds |
|------|-------|
| `src/importer.ts` | `BatchImporter`, where the bug is |
| `src/shelfStore.ts` | `ShelfStore`, a store whose writes take time |
| `src/auditLog.ts` | `AuditLog`, whose entries take time to write |
| `tests/virtual-clock.ts` | The grader's clock; keep this file as it is |
| `tests/level-<n>.test.ts` | The examples of each open level, written by `cstudy` when the level opens; yours to edit, never rewritten |

## Running the tests

From this folder:

```sh
node --test
```

From the workspace, `cstudy test debug-async-batch-typescript` runs the same tests. Node strips the types without checking them; `../../typescript/node_modules/.bin/tsc` here, or `cstudy test --typecheck`, type-checks the project.

Use erasable syntax only (no `enum`, no `namespace`, no constructor parameter properties), and import your own files with their `.ts` extension. Nothing is installed here.

## Testing on the virtual clock

`cstudy` grades and tests this project on a virtual clock, so a wait of any length takes no real time, and a wait that nothing can end is reported at once. `tests/virtual-clock.ts` is the grader's own clock, and `cstudy verify` checks that it has not changed. The generated tests start it with `virtualClock(t)`, and yours can too:

```ts
import assert from "node:assert/strict";
import { test } from "node:test";

import { BatchImporter } from "../src/importer.ts";
import { virtualClock } from "./virtual-clock.ts";

test("a batch of one takes one write and one audit entry", async (t) => {
  const clock = virtualClock(t);
  const importer = new BatchImporter();
  assert.equal(await clock.wait(importer.importAll(["a"])), 1); // the clock moves while it waits
  assert.equal(clock.now(), 150); // the virtual milliseconds since the test started
});
```

Await a promise of your code through `clock.wait`, because a plain `await` would wait for a timer that never fires. `clock.settle()` lets every promise continuation run, and `clock.advance(ms)` moves the clock forward. What is still pending when a test ends is dropped.

## Grading

Your tests are feedback only. `cstudy submit debug-async-batch-typescript` grades every case of the open levels, hidden ones included, and opens the next level when they all pass.
