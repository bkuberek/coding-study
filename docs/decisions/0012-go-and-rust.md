# ADR 0012: Go and Rust are optional languages per problem, then required of every problem

| Field | Value |
|-------|-------|
| Status | Accepted |
| Date | 2026-10-29 |
| Spec | [problem-format](../specs/problem-format.md#type-mapping), [runners](../specs/runners.md#invocation) |

## Context

The catalog is practiced in Python, TypeScript, Java and Kotlin. Go and Rust are the next languages an interview asks for, and both differ from the existing four in ways that shape the design:

- Both compile ahead of time. There is no module to load: a missing function or a wrong signature is a compile error, which conformance fixture 9007 expects as a `load_error`.
- Neither has a reflection API that finds an unexported function by name. Go can call a function value through `reflect`; Rust cannot call anything it was not generated to call.
- "Every language" was spelled `tuple(Language)` in several defaults (`languages` of a problem, `cstudy next`, IDE actions, verify coverage). Adding enum members would have made every problem require Go and Rust references at once, and failed the ready check of all of them.
- The catalog has 218 problems with about 2.3 approaches each. Reference solutions in two more languages are about 1,000 files.

A spike (scratch code, not merged) built a Go runner and a Rust bridge for `two-sum` and an LRU cache, measured builds, and attached Delve and Xcode's `debugserver`. Warm rebuilds after an edit took 0.16 s in Go and 0.34 s in Rust (release profile), against 0.14 and 0.19 s for a trivial program.

## Decision

- **Optional per problem, then required.** `CORE_LANGUAGES` (Python, TypeScript, Java, Kotlin) is what a problem lists by default and what every default means. `OPTIONAL_LANGUAGES` (Go, Rust) are added to a problem's `languages` once its references exist. The schema requires the four core languages and allows `go` and `rust` on top; the concurrency and debugging tracks keep their subset rule. Ready, verify, `start` and `next` already work from the listed languages, so a problem that does not list Go is never offered, started or required in Go.
- **Full backfill, then a flip.** Go and Rust references are written for the whole catalog in batches by pattern, each batch passing the full verify gate. When the backfill reaches every problem, one final change makes all six languages required and `CORE_LANGUAGES` stops being a separate set. Recorded exceptions: `0055-linked-list-cycle` has no Rust reference unless a clean cyclic list representation exists, and the debugging track gets new Go- and Rust-native bug problems instead of ports.
- **Exhaustive language dispatch.** Every `match` on `Language` in layout, targets, buggy stubs, stub checks and the VS Code attach configuration ends in `assert_never`, and a test requires every `Language`-keyed table to hold a row per language, so a forgotten language is a type error or a failing test, never a silent fall-through to JVM paths.
- **Layout.** Go: `go/practice/<snake_slug>/<snake_slug>.go`, one package per problem, so a broken problem never blocks another. Rust: `rust/practice/<snake_slug>.rs`, a Cargo example built as a library crate. References are `solutions/<approach>.go` and `.rs`.
- **Names.** Go is idiomatic: functions `twoSum`, constructors `NewLRUCache`, exported PascalCase methods (reflection only finds exported ones). Rust is snake_case for functions, methods and parameters, with `new` as the constructor. `member_name` takes the role of the name, and the request carries `names.constructor`. Reserved-word check S3 considers only the languages a problem lists.
- **Types.** Rust nodes follow LeetCode: `Option<Box<ListNode>>`, `Option<Rc<RefCell<TreeNode>>>`. Go `char` is `rune`. `decimal` is vendored shopspring/decimal in Go and rust_decimal in Rust, `date` is `time.Time` at UTC midnight and chrono `NaiveDate`; encoders are strict, as in [ADR 0011](0011-decimal-and-date-types.md). A Box list has no identity and cannot be cyclic, which costs exactly one problem.
- **Runners are standard library only.** The libraries for `decimal` and `date` are vendored, and builds run offline (`GOTOOLCHAIN=local`, `GOPROXY=off`, `cargo --offline`), so both languages work offline from the first run.
- **Runner architecture.**
  - Go compiles the user's package with a small generated registration file added through `go build -overlay`, so compiler errors and breakpoints name the real files. A reflective runner checks the types against the DSL and calls the target.
  - Rust has a bridge generated from the signature (decode, call, encode, and a `match` on the operation for classes) over a static runner library. The user's file and every reference enter as `#[path]` modules of a per-problem crate in a shared Cargo workspace and target directory.
  - A request names compiled code with `{"compiled": "user"}` or `{"compiled": "ref/<approach>"}`, since there is no path or class to load.
  - Compile diagnostics in the user's or a reference file mean a build failure (exit 2). Diagnostics only in generated code mean that target gets a `load_error`; the CLI rebuilds without it, at the cost of a second compile in the failure case only.
  - The Rust build uses the release profile with overflow checks and line tables for tests and benches, so `--perf` numbers are real and an `i32` overflow panics instead of wrapping.
- **Environment.** A missing Go or Rust toolchain is a `doctor` warning ("needed for `--lang go`"), not a failure. Debugging is VS Code only (Delve for Go; CodeLLDB with `debugserver` or `lldb-server` for Rust); IntelliJ gets tasks. Go and Rust run concurrent problems in the `threads` model, in a later step.
- **Budgets.** Warm `cstudy test` targets are 1 s for Go and 2 s for Rust. Full verify gets per-language budgets, and `cstudy verify --lang` gates a batch.

## Status

This decision lands in steps. Implemented: the `Language` members, `CORE_LANGUAGES` and `OPTIONAL_LANGUAGES`, the schemas, layout and naming, the per-language tables, and the "not set up yet" error (exit 4) for a listed language without an adapter. Planned and not yet working: stub generators, runners, the workspace template, `doctor` checks, IDE files, `--debug`, concurrency and the references themselves. Until a step lands, the specs mark its Go and Rust rows as planned.

## Consequences

- Existing problems, stubs and requests are unchanged: the four core languages produce byte-identical output, and every default that meant "all languages" now means the core four.
- During the backfill, `cstudy list --lang go` and `cstudy next --lang go` show only the problems that have Go references, and verify coverage lines show Go and Rust once a problem lists them.
- A language that is known but has no adapter fails with `go stub generator is not set up yet` (exit 4) wherever an adapter is needed, and with "not available in go" (exit 3) for a problem that does not list it. `doctor` does not mention Go or Rust until their runners exist.
- Full verify grows: Go adds roughly 0.5 to 1.5 s per problem and Rust 1.5 to 4 s, and Cargo's target-directory lock serializes parallel Rust builds. The oracle and ladder checks cost more per added language.
- Go and Rust references written by agents need review at about twice the current reference volume.
- A cyclic linked list cannot be expressed in Rust with `Box`, so identity-based list problems are Go-only unless a representation is found.

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Require Go and Rust of every problem at once | Blocks the runners behind about 1,000 reference files, fails the ready check of all 218 problems, and doubles the verify cost before anything ships |
| Optional with no backfill plan | `cstudy next --lang go` would offer nothing until someone happened to write references |
| Port the debugging track | Its bugs are language specific (integer overflow and boxed equality are JVM-only, a mutable default argument is Python-only); Go and Rust get bugs of their own |
| Go `package` copy instead of `-overlay` | Compiler errors name the copy and Delve cannot set a breakpoint at the user's path |
| serde or a JSON crate in the Rust runner | About eight vendored crates, proc macros included, for a few hundred lines of codec |
| `byte` for Go `char` | Wrong for non-ASCII; `rune` is exact for the BMP the DSL allows |
| Persistent compile servers | The measured warm rebuilds already meet the budgets, and a daemon is state to keep correct |
