# Runner conformance suite

Fixture problems in the normal problem format ([problem-format](../../docs/specs/problem-format.md)) that every runner must handle the same way. `cstudy verify --conformance` runs every fixture's reference approaches in every language its `meta.yaml` lists (the four core languages by default; Go and Rust where it lists `go` or `rust`), compares each runner outcome with [`expectations.json`](expectations.json) ([schema](../../schemas/conformance.schema.json)), and generates and compiles the stub of every fixture. Spec: [runners](../../docs/specs/runners.md#conformance-suite).

## Layout

| Path | Scope | Content |
|------|-------|---------|
| `<id>-<slug>/meta.yaml`, `<id>-<slug>/tests.json` | Shared by every runner | Signature and cases; a change affects every language the fixture lists |
| `<id>-<slug>/solutions/<approach>.py` | Python runner | Reference approach |
| `<id>-<slug>/solutions/<approach>.ts` | TypeScript runner | Reference approach (named export) |
| `<id>-<slug>/solutions/<approach>.java`, `.kt` | JVM runner | Reference approach without a `package` line; the materializer prepends it |
| `<id>-<slug>/solutions/<approach>.go` | Go runner | Reference approach in `package <snake_slug>`, like the stub; copied unchanged into a package of its own |
| `<id>-<slug>/solutions/<approach>.rs` | Rust runner | Reference approach as the stub declares it (`pub fn`, or `pub struct` with `impl`); built as a `#[path]` module of the problem's harness crate |
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

Stress cases run `runs` times per variant (default 10; JVM fixtures run once per thread kind). With `pass`, at most `max_failed` runs may fail (default 0); with any other status, at least `min_failed` runs (default: every run) must fail with that status, and `message`, `op_index` and `phase` must match each of them. `deterministic` repeats the first seed once more and requires both runs of that seed to produce the same run record and the other seeds at least two distinct records; `restart_requested` requires the runner to ask for a restart after a run of the case. A fixture runs only in the languages its `meta.yaml` lists, which is also how a runner skips what it does not support yet: Go lists 9001 to 9017 and 9019 to 9021. `conformance-stress-async-determinism` (9018) stays Python and TypeScript: it tests the `async` model, and Go and Rust run the `threads` model only. Rust lists the same fixtures as Go except `conformance-cyclic-list` (9006) and `conformance-ref-of-list` (9010), which `cstudy verify` S13 keeps out of Rust for good: an `Option<Box<ListNode>>` cannot be cyclic, and `ref_of` cannot hand out a second reference to one of its nodes ([ADR 0012](../../docs/decisions/0012-go-and-rust.md)).

## What each approach does

Every approach is written once per language, in that language's idiomatic form for the stub signature.

| Fixture | Approach | Behavior | Expected |
|---------|----------|----------|----------|
| `conformance-types` | `identity` | `TypeEcho(label)` ignores `label`; every `echo*` method returns its argument unchanged; `noop` returns nothing. Every DSL type except `decimal` and `date` | pass |
| `conformance-decimal-date-types` | `identity` | The same echo methods for `decimal` and `date`, in scalars, arrays, matrices and lists; a fixture of its own so that a runner can join the suite before it supports them. Go echoes `decimal.Decimal` and `time.Time`, Rust `rust_decimal::Decimal` and `chrono::NaiveDate`; the extremes (28 nines, 28 places, years 0001 and 9999) fit both | pass |
| `conformance-decimal-date` | `arithmetic` | `DecimalDates` adds and totals decimals of mixed scale, rounds to cents half up and half even, prorates a premium (half up), adds days to a date across leap days and counts the days between two dates; inputs keep their scale and outputs are canonical (`2500.00` comes back as `2500`). Go rounds with `Round` and `RoundBank`, prorates with `DivRound` (one exact rounding) and counts days through Unix seconds; Rust rounds with `round_dp_with_strategy` (`MidpointAwayFromZero`, `MidpointNearestEven`) after a 28-digit division, and counts days with `NaiveDate` subtraction | pass |
| `conformance-function` | `identity` | `echoHTTPCodes` returns `firstValue` unchanged | pass |
| `conformance-exception` | `raises` | `failWith` throws with `message` as the exception message: Python `RuntimeError`, TypeScript `Error`, Java `IllegalStateException`, Kotlin `error(...)`, Go `panic(message)`, Rust `panic!("{message}")` | error with that message |
| `conformance-op-error` | `counts` | `increment` adds 1 to a counter starting at 0 and returns it; `fail` throws (Go and Rust: panics) with message `counter failure` | `fails` case: error at `op_index` 3 with `partial_output` `[null, 1, 2]` |
| `conformance-non-finite` | `multiplies` | `scale` returns `value * factor` (`1e308 * 10` overflows to infinity) | `overflow` case: invalid_output |
| `conformance-cyclic-list` | `identity` | `echoList` returns `head` unchanged | `cyclic` case: invalid_output |
| `conformance-missing-symbol` | `misnamed` | Defines `echoNumberTypo` (Python and Rust `echo_number_typo`) with the same signature instead of `echoNumber`; in Go the generated registration and in Rust the generated bridge do not compile, so the runner is rebuilt without the target | load_error |
| `conformance-hang` | `spins` | `waitFor` loops forever when `value` is negative, else returns `value` | `hang` case: timeout |
| `conformance-stdout` | `prints` | `shout` prints `text` on its own line to standard output (`print`, `console.log`, `System.out.println`, `println`, `fmt.Println`, `println!`), then returns `text` | pass with stdout `conformance output\n` |
| `conformance-ref-of-list` | `identity` | `pickNode` returns `node` unchanged | pass |
| `conformance-ref-of-list` | `new-node` | `pickNode` returns a new node with `node`'s value (`as: index` of a node outside `head`) | invalid_output |
| `conformance-ref-of-tree` | `identity` | `pickTreeNode` returns `node` unchanged | pass |
| `conformance-output-from` | `sorts` | `sortValues` sorts `values` ascending in place and returns nothing | pass |
| `conformance-no-alias` | `deep-copy` | `copyList` builds new nodes with the same values | pass |
| `conformance-no-alias` | `returns-input` | `copyList` returns `head` unchanged | invalid_output, except `empty`: pass |
| `conformance-stress-counter` | `atomic` | `increment` adds 1 under a lock (`AtomicInteger` on the JVM, `sync.Mutex` in Go, `Mutex<i32>` in Rust) and returns the new count | `s1`: pass 10 of 10 |
| `conformance-stress-counter` | `racy` | `increment` reads the count on one line and writes it on the next (TypeScript awaits between them; in Go a plain data race, in Rust a relaxed atomic load and a separate store, since safe Rust has no data race), returning the count it wrote | `s1`: fail (`distinct`) in at least 9 of 10 |
| `conformance-stress-stall` | `never-opens` | `enter` waits on a gate nobody opens (`Event`, `CountDownLatch`, a promise that never settles, a channel nobody closes, a `Condvar` nobody notifies) | `s1`: stalled |
| `conformance-stress-worker-error` | `throws-at` | `step` returns `index`, and throws `failed at 100` when `index` is 100 | `s1`: error, phase `worker`, op 100 |
| `conformance-stress-sections` | `locked` | `lock` and `unlock` use a real mutex (an async one with a waiter queue in TypeScript, `sync.Mutex` in Go, a flag under a `Mutex` with a `Condvar` in Rust, whose `MutexGuard` cannot outlive `lock`) | `s1`: pass 10 of 10, no probe violations |
| `conformance-stress-sections` | `unlocked` | `lock` and `unlock` do nothing | `s1`: fail (`section`) in at least 9 of 10 |
| `conformance-stress-async-determinism` | `interleaves` | `append` yields once, appends and returns the length (Python async and TypeScript only) | `s1`: pass, identical records for one seed, distinct across seeds |
| `conformance-stress-leak` | `ignores-interrupt` | `spin` loops forever ignoring interrupts, `fail` throws (threads only; Go and Rust have no interrupt at all, and neither a goroutine nor a thread can be stopped from outside) | `s1`: error, then `restart_requested`; `s2` still runs and passes |
