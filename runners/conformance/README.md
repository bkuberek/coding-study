# Runner conformance suite

Fixture problems in the normal problem format ([problem-format](../../docs/specs/problem-format.md)) that every runner must handle the same way. `cstudy verify --conformance` runs every fixture's reference approaches in all four languages, compares each runner outcome with [`expectations.json`](expectations.json) ([schema](../../schemas/conformance.schema.json)), and generates and compiles the stub of every fixture. Spec: [runners](../../docs/specs/runners.md#conformance-suite).

## Layout

| Path | Scope | Content |
|------|-------|---------|
| `<id>-<slug>/meta.yaml`, `<id>-<slug>/tests.json` | Shared by every runner | Signature and cases; a change affects all four languages |
| `<id>-<slug>/solutions/<approach>.py` | Python runner | Reference approach |
| `<id>-<slug>/solutions/<approach>.ts` | TypeScript runner | Reference approach (named export) |
| `<id>-<slug>/solutions/<approach>.java`, `.kt` | JVM runner | Reference approach without a `package` line; the materializer prepends it |
| `expectations.json` | Shared by every runner | Expected outcome per fixture and approach |

## Outcomes

| Status | Meaning |
|--------|---------|
| `pass` | The runner reports `ok` and the fixture's comparator accepts the output; `stdout`, when given, must match exactly |
| `error` | The runner reports `error`; `message`, `op_index` and `partial_output`, when given, must match exactly |
| `invalid_output` | The runner reports `invalid_output` (any reason text) |
| `timeout` | The CLI hang guard kills the runner on this case, and the later cases still run |
| `load_error` | The runner reports `load_error` for the job instead of any case |
| `fail` | Stress cases: the run completed but broke an invariant or `final.expected` |
| `stalled` | Stress cases: workers were still unfinished at the deadline; `progress` names a worker inside an op |

Stress cases run `runs` times per variant (default 10; JVM fixtures run once per thread kind). With `pass`, at most `max_failed` runs may fail (default 0); with any other status, at least `min_failed` runs (default: every run) must fail with that status, and `message`, `op_index` and `phase` must match each of them. `deterministic` repeats the first seed once more and requires both runs of that seed to produce the same run record and the other seeds at least two distinct records; `restart_requested` requires the runner to ask for a restart after a run of the case. A fixture runs only in the languages its `meta.yaml` lists.

## What each approach does

Every approach is written once per language, in that language's idiomatic form for the stub signature.

| Fixture | Approach | Behavior | Expected |
|---------|----------|----------|----------|
| `conformance-types` | `identity` | `TypeEcho(label)` ignores `label`; every `echo*` method returns its argument unchanged; `noop` returns nothing | pass |
| `conformance-function` | `identity` | `echoHTTPCodes` returns `firstValue` unchanged | pass |
| `conformance-exception` | `raises` | `failWith` throws with `message` as the exception message: Python `RuntimeError`, TypeScript `Error`, Java `IllegalStateException`, Kotlin `error(...)` | error with that message |
| `conformance-op-error` | `counts` | `increment` adds 1 to a counter starting at 0 and returns it; `fail` throws with message `counter failure` | `fails` case: error at `op_index` 3 with `partial_output` `[null, 1, 2]` |
| `conformance-non-finite` | `multiplies` | `scale` returns `value * factor` (`1e308 * 10` overflows to infinity) | `overflow` case: invalid_output |
| `conformance-cyclic-list` | `identity` | `echoList` returns `head` unchanged | `cyclic` case: invalid_output |
| `conformance-missing-symbol` | `misnamed` | Defines `echoNumberTypo` (Python `echo_number_typo`) with the same signature instead of `echoNumber` | load_error |
| `conformance-hang` | `spins` | `waitFor` loops forever when `value` is negative, else returns `value` | `hang` case: timeout |
| `conformance-stdout` | `prints` | `shout` prints `text` on its own line to standard output (`print`, `console.log`, `System.out.println`, `println`), then returns `text` | pass with stdout `conformance output\n` |
| `conformance-ref-of-list` | `identity` | `pickNode` returns `node` unchanged | pass |
| `conformance-ref-of-list` | `new-node` | `pickNode` returns a new node with `node`'s value (`as: index` of a node outside `head`) | invalid_output |
| `conformance-ref-of-tree` | `identity` | `pickTreeNode` returns `node` unchanged | pass |
| `conformance-output-from` | `sorts` | `sortValues` sorts `values` ascending in place and returns nothing | pass |
| `conformance-no-alias` | `deep-copy` | `copyList` builds new nodes with the same values | pass |
| `conformance-no-alias` | `returns-input` | `copyList` returns `head` unchanged | invalid_output, except `empty`: pass |
| `conformance-stress-counter` | `atomic` | `increment` adds 1 under a lock (`AtomicInteger` on the JVM) and returns the new count | `s1`: pass 10 of 10 |
| `conformance-stress-counter` | `racy` | `increment` reads the count on one line and writes it on the next (TypeScript awaits between them), returning the count it wrote | `s1`: fail (`distinct`) in at least 9 of 10 |
| `conformance-stress-stall` | `never-opens` | `enter` waits on a gate nobody opens (`Event`, `CountDownLatch`, a promise that never settles) | `s1`: stalled |
| `conformance-stress-worker-error` | `throws-at` | `step` returns `index`, and throws `failed at 100` when `index` is 100 | `s1`: error, phase `worker`, op 100 |
| `conformance-stress-sections` | `locked` | `lock` and `unlock` use a real mutex (an async one with a waiter queue in TypeScript) | `s1`: pass 10 of 10, no probe violations |
| `conformance-stress-sections` | `unlocked` | `lock` and `unlock` do nothing | `s1`: fail (`section`) in at least 9 of 10 |
| `conformance-stress-async-determinism` | `interleaves` | `append` yields once, appends and returns the length (Python async and TypeScript only) | `s1`: pass, identical records for one seed, distinct across seeds |
| `conformance-stress-leak` | `ignores-interrupt` | `spin` loops forever ignoring interrupts, `fail` throws (threads only) | `s1`: error, then `restart_requested`; `s2` still runs and passes |
