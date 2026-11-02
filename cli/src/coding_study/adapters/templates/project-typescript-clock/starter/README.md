# {{title}}

TODO: one paragraph on what this project builds over its levels.

## Contract

- `src/main.ts` exports the class `{{class_name}}` by name. Keep the file and the export where they are: `cstudy submit` imports `{{class_name}}` from `src/main.ts`.
- `new {{class_name}}()` takes no arguments.
- Each level names the methods it adds, with their parameters and return types; a method that waits returns a `Promise`. Keep those names and signatures.

Everything else is yours: add modules under `src/`, and your own tests under `tests/`.

## Running the tests

From this folder:

```sh
node --test
```

From the workspace, `cstudy test {{slug}}` runs the same tests. Node strips the types without checking them; `../../typescript/node_modules/.bin/tsc` here, or `cstudy test {{slug}} --typecheck`, type-checks the project.

Use erasable syntax only (no `enum`, no `namespace`, no constructor parameter properties), and import your own files with their `.ts` extension. Keep `package.json` free of dependencies: the project uses the workspace's Node and TypeScript, and nothing is installed here.

## Testing on the virtual clock

`cstudy` grades and tests this project on a virtual clock: `node:test`'s mock timers, which `tests/virtual-clock.ts` moves from one due timer to the next, so a wait of any length takes no real time. Keep that file as it is: it is the grader's own clock, and `cstudy verify` checks that it has not changed. The generated tests in `tests/` start it with `virtualClock(t)`; write yours the same way:

```ts
import assert from "node:assert/strict";
import { test } from "node:test";

import { {{class_name}} } from "../src/main.ts";
import { virtualClock } from "./virtual-clock.ts";

test("a wait ends when a value arrives", async (t) => {
  const clock = virtualClock(t);
  const store = new {{class_name}}();
  const waiter = store.waitFor("a", 5000);
  await clock.settle(); // every promise continuation has run
  await clock.advance(1000); // the clock moves one second forward
  store.put("a", "x");
  assert.equal(await clock.wait(waiter), "x"); // the clock moves while it waits
  assert.equal(clock.now(), 1000); // the virtual milliseconds since the test started
});
```

Read the time with `Date.now()` and wait with `setTimeout`, `setInterval` or `setTimeout` from `node:timers/promises`, looked up when the code waits: a timer function stored before the test started is the real one, which the clock cannot move. Await a promise of your code through `clock.wait`, which moves the clock while it is pending; a plain `await` would wait for a timer that never fires. A wait that no timer can end is a deadlock: `clock.wait` throws a `DeadlockError` at once, and `cstudy submit` reports the case as `STALLED` with the operation and the virtual time. What is still pending when a test ends is dropped.

Events due at the same instant happen in no fixed order, so the expected values never depend on it.

## Grading

Your tests are feedback only. `cstudy submit {{slug}}` grades every case of the open levels, hidden ones included, and opens the next level when they all pass.
