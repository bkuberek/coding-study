# Vendor Retry Client

The client the company uses to reach its rates vendor. It sends one request and reports what came back. The vendor is unreliable, so that is not good enough.

## Contract

- `src/ratesClient.ts` exports the class `RatesClient` by name, and `new RatesClient()` takes no arguments. Keep the file and the export where they are: `cstudy submit` imports the class from there.
- Each level names the methods it adds, with their parameters and return types; `call` returns a `Promise`. Keep those names and signatures.

Everything else is yours to change, move or add to.

## Layout

| Path | Holds |
|------|-------|
| `src/ratesClient.ts` | `RatesClient`: what the rest of the company calls |
| `src/vendor/scriptedVendor.ts` | `ScriptedVendor`: the vendor as far as the client can see it, scripted by the tests |
| `src/timing/sleep.ts` | `sleep`: a wait on the clock |
| `src/timing/jitter.ts` | `JitterSource`, the interface, and `ScriptedJitter`, a source tests can script |
| `src/json.ts` | `canonicalJson`: JSON with object keys in sorted order |
| `tests/vendor.test.ts` | Tests of how the vendor and the jitter source behave |
| `tests/virtual-clock.ts` | The grader's clock; keep this file as it is |
| `tests/level-<n>.test.ts` | The examples of each open level, written by `cstudy` when the level opens; yours to edit, never rewritten |

## Running the tests

From this folder:

```sh
node --test
node --test tests/level-1.test.ts
```

From the workspace, `cstudy test vendor-retry-client-typescript` runs the same tests. Node strips the types without checking them; `../../typescript/node_modules/.bin/tsc` here, or `cstudy test --typecheck`, type-checks the project.

Use erasable syntax only (no `enum`, no `namespace`, no constructor parameter properties), and import your own files with their `.ts` extension. Nothing is installed here.

## Testing on the virtual clock

`cstudy` grades and tests this project on a virtual clock, so a wait of any length takes no real time, and a wait that nothing can end is reported at once. `tests/virtual-clock.ts` is the grader's own clock, and `cstudy verify` checks that it has not changed. The generated tests start it with `virtualClock(t)`, and yours can too:

```ts
import assert from "node:assert/strict";
import { test } from "node:test";

import { RatesClient } from "../src/ratesClient.ts";
import { virtualClock } from "./virtual-clock.ts";

test("past the end of the script the vendor answers 200 after 10 ms", async (t) => {
  const clock = virtualClock(t);
  const client = new RatesClient();
  await clock.wait(client.call("GET", "/rates", "")); // the clock moves while it waits
  assert.equal(clock.now(), 10); // the virtual milliseconds since the test started
});
```

Await a promise of your code through `clock.wait`, because a plain `await` would wait for a timer that never fires. `clock.settle()` lets every promise continuation run, and `clock.advance(ms)` moves the clock forward. What is still pending when a test ends is dropped.

Read the time with `Date.now()` and wait with `setTimeout`, looked up when you wait. The clock can see nothing else, and it cannot move a timer function stored before it started.

## Grading

Your tests are feedback only. `cstudy submit vendor-retry-client-typescript` grades every case of the open levels, hidden ones included, and opens the next level when they all pass. Each submission grades the earlier levels again.
