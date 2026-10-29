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

This decision lands in steps. Implemented: the `Language` members, `CORE_LANGUAGES` and `OPTIONAL_LANGUAGES`, the schemas, layout and naming, the per-language tables, and the "not set up yet" error (exit 4) for a listed language without an adapter. Go and Rust each: the stub generator, the runner for function, design and progressive problems in test and bench mode, the workspace's `go/` or `rust/` project, conformance fixtures 9001 to 9013 (Rust without 9006 and 9010, see below), and references for `two-sum`, `lru-cache` and `invert-binary-tree`. Planned and not yet working: `decimal` and `date`, concurrency and `--debug` in both; Go and Rust `doctor` checks and IDE files; the rest of the references. Until a step lands, the specs mark its rows as planned.

## Amendments

Settled while building the Go runner (2026-10-29):

- **Go 1.24 or newer.** The build parses `go build -json`, which Go 1.24 introduced. The workspace's `go/go.mod` and the generated build module say `go 1.24`; the runner module itself needs only Go 1.22.
- **Package clause.** Reference and buggy files declare `package <snake_slug>`, the stub's own clause, and are copied unchanged, so a file moves between `solutions/` and the practice directory as is. Unlike the JVM, nothing is rewritten: Go does not require a package's name to match its directory, each approach still gets a package of its own, and the generated registration repeats whatever clause the file declares.
- **Support types live in the runner module.** `cstudy/support` is part of the runner module `cstudy`, which the workspace's `go.mod` replaces with `../.cs/runtime/runners/go`. A copy in the workspace module would give the runner and the solution two different `ListNode` types.
- **A missing symbol keeps the compiler's reason.** The second build passes the failing registrations' messages to the runner, so the `load_error` says why, for example `undefined: twoSum` or `cannot use generic function twoSum without instantiation`.
- **Concurrent `cstudy` processes.** The build holds an exclusive lock, and every process runs its own copy of the binary, so a build in one process never replaces the file another is about to start.
- **Per-language conformance.** The `decimal` and `date` round trips moved out of `conformance-types` into `conformance-decimal-date-types` (9021). A fixture runs in the languages its `meta.yaml` lists, so Go lists the fixtures it supports and needs no skip list in `expectations.json`.
- **The user's Go settings stay out of builds.** The go command reads an empty `GOFLAGS` as unset and falls back to the file `go env -w` writes, where `GOFLAGS=-mod=mod` failed every build in workspace mode. Builds run with `GOENV=off` and `GOFLAGS=-mod=readonly`, without the user's `GOOS`, `GOARCH` and `GOWORK`.

Settled while building the Rust runner (2026-10-29):

- **One harness package per problem and scope.** `.cs/build/rust` holds `test/`, `verify/` and `bench/` packages named `<scope>_<snake_slug>`, like Go's binaries per scope, so a broken reference never blocks `cstudy test` and the user's file never blocks `verify`. The workspace lists its members one by one: Cargo reads a glob that matches nothing as a path.
- **Edition 2021, Rust 1.80 or newer.** LeetCode's edition; the user's file compiles as a module of the harness crate, so the harness's edition is the user's. `rust/Cargo.toml` needs a target before the first problem starts, so it has an empty `lib.rs`.
- **Errors in the user's terms.** The bridge's module `user` is the file's name in a `load_error`, rustc's similar-name hint is kept, a private function says to declare it `pub`, and for a type mismatch the message says which side is the user's: rustc's "expected" is the user's parameter type for an argument, but the declared type for the result.
- **Identity is a node's address.** `no_alias_with` works on lists too: the call runs with freed memory retained (the runner's allocator skips frees during it), so a new node can never take the address of an input node the function dropped. `ref_of` and `as: index` on a list cannot work, since they need a second reference to a node a `Box` owns, and neither can a cyclic list input. Static check S13 keeps `rust` out of such problems: `0055-linked-list-cycle` and conformance fixtures 9006 and 9010.
- **Memory is `heap_peak`, high confidence.** A counting global allocator in `cs_runner` counts the case thread's allocations during the separate memory call only, from zero at its start; elsewhere an allocation pays one thread-local read.
- **The user's Cargo setup stays out of builds.** Builds run with empty `CARGO_ENCODED_RUSTFLAGS`, `RUSTC_WRAPPER` and `RUSTC_WORKSPACE_WRAPPER`, `--target <host>` and the release profile repeated as `--config`, without the user's `RUSTFLAGS`, `CARGO_TARGET_DIR`, `CARGO_BUILD_*` and `CARGO_PROFILE_*`, so a configured wrapper, rustflags, target or profile cannot break a build or change its semantics.
- **Panics.** A panic's `error.type` is `panic` (Rust panics have no type). The trace keeps the backtrace frames in the target's file, and the panic's location (indexing, overflow and `unwrap` report the user's line) stands in for an innermost function the release build inlined without a location.
- **Graph neighbors.** `GraphNode.neighbors` is `Vec<Rc<RefCell<GraphNode>>>`: a null neighbor is invalid, so the elements are not `Option`s.

## Consequences

- Existing problems, stubs and requests are unchanged: the four core languages produce byte-identical output, and every default that meant "all languages" now means the core four.
- During the backfill, `cstudy list --lang go` and `cstudy next --lang go` show only the problems that have Go references, and verify coverage lines show Go and Rust once a problem lists them.
- A language that is known but has no adapter fails with `rust stub generator is not set up yet` (exit 4) wherever an adapter is needed, and with "not available in rust" (exit 3) for a problem that does not list it. `doctor` does not mention Go or Rust until their runners exist.
- Full verify grows: Go adds roughly 0.5 to 1.5 s per problem and Rust 1.5 to 4 s, and Cargo's target-directory lock serializes parallel Rust builds. The oracle and ladder checks cost more per added language.
- Go and Rust references written by agents need review at about twice the current reference volume.
- A cyclic linked list cannot be expressed in Rust with `Box`, so cyclic-list and list `ref_of` problems are Go-only (S13); `no_alias_with` on a list works in Rust.

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
