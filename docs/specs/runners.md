# Spec: Runners and Stub Generation

A runner is a small program per runtime that loads one target (the user's file, a reference approach, or a [project folder](#project-jobs)), deserializes case inputs, invokes the target, and serializes outputs or measurements. It never sees expected values and never judges results. There are five runners: Python, TypeScript, JVM (shared by Java and Kotlin), Go and Rust ([ADR 0012](../decisions/0012-go-and-rust.md)). Rows and fields below marked planned describe parts that nothing implements yet.

## Decisions

| Decision | Choice | Rejected alternative |
|----------|--------|----------------------|
| Who compares | CLI core (Python, once) | Comparators in each runner: 3 implementations of float, multiset and checker logic |
| Result channel | JSON Lines written to a file passed as `--out` | stdout: user `print` calls would corrupt the protocol |
| User output | Captured per case inside the runner, truncated to 4 KiB with a fixed notice, returned in the event | Interleaved terminal output with no case attribution |
| Hang protection | CLI-side inactivity watchdog kills the process group | In-runner timeouts: Python and JVM cannot safely kill a running thread |
| Batching | One process runs many jobs (verify, bench) | One process per problem: JVM start cost x 200 |
| Concurrent stress | The CLI expands scenarios and judges invariants; runners execute literal per-worker scripts and record results ([Concurrent jobs](#concurrent-jobs)) | Scenario templates and invariants in each runner |

## Invocation

| Runner | Prepare (before each run) | Command | cwd |
|--------|---------------------------|---------|-----|
| Python | none (`cstudy doctor --fix` runs `uv sync` once) | `python/.venv/bin/python -m cs_runner --request R --out O` | `python` |
| TypeScript | none | `node .cs/runtime/runners/typescript/runner.ts --request R --out O` | `typescript` |
| Java | `./gradlew -q --console=plain :java:csClasspath -Pcs.only=<snake_slug>` | `java -cp <classpath> cs.runner.Main --request R --out O` | `jvm` |
| Kotlin | `./gradlew -q --console=plain :kotlin:csClasspath -Pcs.only=<snake_slug>` | same as Java | `jvm` |
| Go | `go build -json [-overlay gen/<snake_slug>/overlay.json] -o bin/<scope>/<snake_slug> ./cmd/<scope>/<snake_slug>` in `.cs/build/go` ([Go build details](#go-build-details)) | `.cs/build/go/run/<pid>-<random>/<snake_slug> --request R --out O`, a private copy of the binary | `.cs/build/go` |
| Rust | `cargo build --offline --release --message-format=json --target <host> -p <scope>_<snake_slug>` in `.cs/build/rust`, with one shared `CARGO_TARGET_DIR` ([Rust build details](#rust-build-details)) | `.cs/build/rust/run/<pid>-<random>/<scope>_<snake_slug> --request R --out O`, a private copy of the binary | `.cs/build/rust` |

Paths are relative to the workspace root. The runners themselves run from the workspace's [runner runtime](installation-and-workspaces.md#runner-runtime) in `.cs/runtime/runners/`, a copy of the content's `runners/` that `cstudy` refreshes before the first runner of a command when the content changed. `R` and `O` live in `.cs/runs/<run_id>/` as `request-<n>.json` and `events-<n>.jsonl`, one pair per restart `n`; the last 20 runs are kept. The process starts in its own process group.

A [project job](#project-jobs) starts in the project root instead: the Python runner adds `-P` and its own environment there, Go launches binaries of its own ([Go project jobs](#go-project-jobs)), and Java and Kotlin build the project folder with its own Gradle build ([JVM project builds](#jvm-project-builds)).

### JVM build details

| Item | Rule |
|------|------|
| `-Pcs.only=<snake_slug>` | Restricts the main source set to `practice/<snake_slug>/**`, so a broken file for another problem never blocks this one. IntelliJ builds without the property and sees everything. |
| `csClasspath` task | Depends on `classes`; writes the runtime classpath (classes dir plus runner and support jars) to `build/cs/runtime-classpath.txt` |
| Gradle settings | Daemon on, configuration cache on, `org.gradle.console=plain` |
| JVM flags | `-XX:+UseSerialGC -Xshare:auto`; no tiering flags (they distort performance cases) |
| Compile errors | Gradle exit code non-zero: the CLI prints compiler lines mentioning the user's file (max 40 lines) and exits 2 |
| Cold start | If no daemon is running, the CLI prints `warming Gradle daemon (first run)` before building |
| Locking | `-Pcs.only` narrows each build to one problem, so every build rewrites the shared output directories and deletes the classes of the problem built before. Per Gradle project and language, one `cstudy` process at a time writes the reference sources (and removes the other approaches' files), runs Gradle and copies the built class directories: an exclusive `flock` on `.cs/build/jvm-locks/<references or practice>-<lang>.lock`. A process that finds the lock taken prints `waiting for another cstudy build in this workspace` and waits; the kernel drops the lock when its holder ends, however it ends. Java and Kotlin use different locks and still build side by side. |
| Runtime jars | Both Gradle projects include the runtime's `runners/jvm` build, so any build after a change to the runner's sources rebuilds `runner.jar` and `support.jar`, and Gradle writes a jar in place: two builds doing so at once, or a JVM reading a jar while it is rewritten, failed before `hello` (`NoClassDefFoundError`). Every build also holds `.cs/build/jvm-locks/runtime.lock`: shared while the runtime's sources and jars (path, size and modification time) are as the last build under the exclusive lock left them, recorded in `runtime-jars.txt`, and exclusive otherwise. So the first builds after a change take turns, and later ones still run side by side. |
| Per-run class copy | Under the locks, the build's class directories (the classpath entries below the subproject's `build/`) and the runtime's runner and support jars are copied into `.cs/build/jvm-runs/<pid>-<random>/`, and the JVM's `-cp` names the copies; the jars in Gradle's cache keep their paths. A later build, for another problem or after a change to the runner, cannot take classes away from a JVM that loads them lazily. The runner process removes the copy when the run ends (completed, failed or interrupted); the next preparation removes copies whose process no longer exists (killed). |

The lock and the copy protect against other `cstudy` processes. A Gradle build started by anything else on the same project (a script, an IDE build of `.cs/build/jvm`) does not take the lock and can still delete classes between the build and the copy.

### Go build details

| Item | Rule |
|------|------|
| Toolchain | Go 1.24 or newer (`go build -json`). Environment `GOENV=off`, `GOTOOLCHAIN=local`, `GOPROXY=off`, `GOFLAGS=-mod=readonly`, `GO111MODULE=on` and `GOWORK=.cs/build/go/go.work`, with the user's `GOOS` and `GOARCH` removed, so a build never downloads a toolchain or a module and builds for this machine whatever the user's `go env -w` file or environment says (an empty `GOFLAGS` would not do: the go command reads it as unset and falls back to that file); the user's build cache is kept, so the standard library and the runner compile once per machine |
| Build module | `.cs/build/go` is module `csbuild`, which requires `cstudy` and the vendored modules; its `go.work` uses it and the workspace's `go/` (module `workspace`), replaces the runner module `cstudy` with `.cs/runtime/runners/go` and each vendored module with its copy there |
| Vendored modules | `github.com/shopspring/decimal` v1.5.0, the Go type of `decimal`, is copied into `runners/go/third_party/github.com/shopspring/decimal` (its `go.mod`, `LICENSE`, `README.md` and non-test sources; `runners/go/third_party/README.md` records the source and hash). `runners/go/go.mod`, the workspace's `go/go.mod` and the build's `go.work` reach it through `replace`, so no build or editor needs the network or a module cache. A `go/go.mod` written before the module was vendored still builds, since the build's `go.work` supplies the `replace`, but the editor cannot resolve the import until its `require` and `replace` lines are added |
| Binary | One per problem and scope (`test`, `verify`, `bench`): `cmd/<scope>/<snake_slug>/main.go` imports the user's package `workspace/practice/<snake_slug>` and each reference package `csbuild/ref/<snake_slug>/<approach_snake>`, and passes their registrations, and the thunks of class kinds, to `runner.Main` keyed by target id (`user`, `ref/<approach>`) |
| Registration | Each package gets `zz_cs_targets.go`: `var CsTargets = map[string]any{"twoSum": twoSum}`, or the constructor (`NewLRUCache`) for class kinds, under the package clause read from its file. The user's enters through `go build -overlay` (the replacement file is `gen/<snake_slug>/user_targets.go`), so nothing is written to `go/practice` and compiler errors and breakpoints name the real file; a reference's is written next to its copy |
| Method thunks | A design or progressive package also gets `zz_cs_thunks.go` (the user's replacement file is `gen/<snake_slug>/zz_cs_thunks.go`), apart from the registration so that it can be left out alone. `var CsThunks` holds a nil `*Class` as `Receiver` and, for each declared method, a function that asserts the receiver and each argument to the Go type of the [mapping](problem-format.md#go-and-rust-mapping) and returns the result as an `any`: `"Insert": func(r any, a []any) any { return r.(*RandomizedSet).Insert(a[0].(int)) }`, with `return nil` after a method that returns nothing. Node types are spelled `*support.ListNode`, so the file does not depend on the stub's aliases, and it imports only what its parameter types use. A function problem gets none (it is called once per input), and neither does a concurrent class (stress workers keep reflection and it has no bench) |
| Method dispatch | The runner still checks every signature by reflection when a job loads, so the result of a mismatch does not depend on the thunks. It calls a method through its thunk when the type the constructor returns is the thunks' `Receiver`, and through `reflect.Value.Call` otherwise, so a class that returns another type or has no thunk keeps working. In a bench the arguments of every operation are decoded to `[]any` before the clock starts, as they are decoded for reflection, and the test path uses the same thunks, so a case produces its results the same way in both. A traceback leaves out the frames of `zz_cs_thunks.go`. The point is the timed region: a reflective call costs about 120 to 250 ns and four allocations per operation, a constant per call that hides a cheap quadratic scan from the [ladder check](performance-analysis.md#ladder-check) (a linear list scan over at most 10^5 values measured about n^1.4, and its time / n^2 varied 5 to 8 times against the 4x tolerance); a thunk call costs about 10 to 20 ns |
| Compile errors | Diagnostics in the user's or a reference file: exit 2 with the compiler lines, paths relative to the workspace (at most 40); in a bench, a reference's are a content error. Diagnostics only in registration files: the build runs again without those registrations (a second compile in that case only), and the runner reports `load_error` `SymbolNotFound` with the compiler's message, such as `the package defines no function "twoSum": undefined: twoSum`. Diagnostics in a thunk file mean a method whose parameters differ from the signature, or a class type that is missing: the same second build leaves that file's thunks out (the file stays, empty), and the runner reports `SignatureMismatch` or `SymbolNotFound` from its own check. A failure with no diagnostics, or with diagnostics in the runner or the main package, is an environment error (exit 4) with the output tail |
| Concurrent `cstudy` processes | Generation and build hold an exclusive `flock` on `.cs/build/go/.cstudy.lock`. The launched file is `run/<pid>-<random>/<snake_slug>`, a copy of the built binary that no other build overwrites; `RunnerProcess` removes its directory when the run ends (completed, failed or interrupted), and the next build removes the directories of processes that no longer exist (killed) |
| Writes | Generated files are rewritten only when their content changes |
| Cold start | Before the first build of a workspace the CLI prints `compiling the Go runner and standard library (first run)`; the build note is `go, cold`, then `go, warm` |
| Debug build | `cstudy test --debug` adds `-gcflags=all=-N -l` (no optimizations, no inlining, so every line and variable of the user's code can be inspected) and writes `bin/debug/<snake_slug>`, apart from the optimized binaries. The first debug build compiles the standard library again; before it the CLI prints `compiling the Go runner and standard library for debugging (first debug run)` ([debug mode](#debug-mode)) |

### Rust build details

| Item | Rule |
|------|------|
| Toolchain | Rust 1.80 or newer through rustup (`cargo` and `rustc` on PATH). The runner crates, the generated harness packages and the practice project declare `rust-version = "1.80"`, so clippy flags APIs newer than that (`incompatible_msrv`). The runner crates' only dependencies are vendored, so builds run with `--offline`, and without `--locked`, which fails whenever a harness package joins the workspace. The host target triple comes from `rustc -vV` once and is kept in `.cs/build/rust/host-target` |
| Build workspace | `.cs/build/rust` is a Cargo workspace with one harness package per problem and scope (`test/<snake_slug>`, `verify/<snake_slug>`, `bench/<snake_slug>`, package `<scope>_<snake_slug>`), listed one by one because Cargo reads a glob that matches nothing as a path. Each package depends on `cs_runner` and `cs_support` in `.cs/runtime/runners/rust` by relative path, and on `rust_decimal` and `chrono` as `cs_runner` declares them, so a solution's `use rust_decimal::Decimal;` resolves; `CARGO_TARGET_DIR=.cs/build/rust/target` is shared, so the runner crates compile once per workspace |
| Vendored crates | `rust_decimal` 1.43.0 (feature `maths`) and `chrono` 0.4.45 (feature `std`), the types of `decimal` and `date`, without default features, and their dependencies `arrayvec`, `num-traits` and `autocfg`, are copied into `runners/rust/vendor` by `cargo vendor`, without their tests, benches and examples (`runners/rust/vendor/README.md`). Every build passes `--config source.crates-io.replace-with="cstudy-vendor"` and `--config source.cstudy-vendor.directory="<runtime>/rust/vendor"`, which outrank a user's `config.toml`, so crates.io is never contacted and a fresh `CARGO_HOME` builds as well as a warm one. `rust_decimal`'s `std` feature is left out: it adds only an `Error` impl, but its weak `dep?/std` features would lock, and so vendor, 48 optional crates |
| Bridge | Each package's `main.rs` is generated from the signature. The user's file and each reference copy enter as `#[path = "<absolute file>"] mod user;` and `mod ref_<approach_snake>;`, so compiler errors, panics and breakpoints name the real file. Per target, the bridge decodes every argument with its declared Rust type, calls the function (`user::two_sum(arg_nums, arg_target)`), or for a class kind `LRUCache::new` and a `match` on the operation's canonical name, and boxes the result for encoding. A name that is a Rust keyword is a raw identifier in the stub and the bridge (`instance.r#move(arg_source, arg_target)`), while the operation stays `move`. A concurrent class is registered as `Entry::Concurrent`: its constructor hands the instance to `cs_runner::shared`, which requires `Send + Sync` (a `RefCell` or `Rc` field is a `load_error` `SignatureMismatch` such as `` `RefCell<VecDeque<i32>>` cannot be shared between threads safely ``), and every decoded call is `Send`, so a concurrent problem with node types cannot run in Rust (`load_error` `UnsupportedType`). Modifiers are generated too: a `ref_of` argument is looked up after the argument it points into, and `as: index` and `no_alias_with` take the parameter's node addresses before the call, which runs with freed memory retained so no new node can reuse an old node's address ([Node modifiers](#node-modifiers)) |
| Release profile | `opt-level = 3`, `overflow-checks = true`, `debug = "line-tables-only"`, `panic = "unwind"`, `strip = "none"` and the platform's default `split-debuginfo` (`"unpacked"` on macOS, `"off"` on Linux), in the workspace manifest and again as `--config profile.release.*`, which outranks a user's `config.toml`: `--perf` numbers are real, an `i32` overflow panics instead of wrapping, traces have line numbers and function names, and a panic is caught per case |
| The user's Cargo setup | Cannot break or redirect a build: `CARGO_ENCODED_RUSTFLAGS` is set empty (it outranks `RUSTFLAGS` and every `rustflags` setting), `RUSTC_WRAPPER` and `RUSTC_WORKSPACE_WRAPPER` are set empty (which turns off a configured wrapper such as sccache), `--target <host>` overrides a configured `build.target`, and the user's `RUSTFLAGS`, `CARGO_TARGET_DIR`, `CARGO_BUILD_*` and `CARGO_PROFILE_*` variables are removed |
| Compile errors | Classified by the primary span of each error-level compiler message only: a call whose signature does not match also gets a child note "function defined here" in the user's file. Errors in the user's or a reference file: exit 2 with `path:line:column: error[<code>]: <message>`, the span's label and up to two `help` or `note` lines (one that suggests a replacement first), paths relative to the workspace (at most 40 lines); in a bench, a reference's are a content error. Errors only in the bridge: the build runs again with those targets marked unavailable, keeping their `mod` so a hidden error in their file still fails the build, and the runner reports `load_error` with the compiler's message in the user's terms, where a keyword name is the signature's (`move`, not `r#move`). `SymbolNotFound` keeps only the compiler's suggestions when it has any: ``cannot find function `two_sum` in `two_sum.rs`; a function with a similar name exists: `twosum` ``, ``no method named `get` found for mutable reference `&mut LRUCache` in the current scope; there is a method `gett` with a similar name``, ``function `two_sum` is private; declare it pub``. `SignatureMismatch`: ``mismatched types: parameter `nums` is `&[i32]`, the signature declares `Vec<i32>` ``, ``mismatched types: the result is `Vec<usize>`, the signature declares `Vec<i32>` ``. A failure with no compiler error, or errors in the runner crates, is an environment error (exit 4) with the output tail |
| Concurrent `cstudy` processes, writes, cold start | As in Go: generation and build hold an exclusive `flock` on `.cs/build/rust/.cstudy.lock`, every run launches its own copy of the binary (`run/<pid>-<random>/<scope>_<snake_slug>`, removed when the run ends, as in Go), and generated files are rewritten only when their content changes (Cargo fingerprints sources by modification time, so rewriting identical bytes would rebuild). Before the first build of a workspace the CLI prints `compiling the Rust runner (first run)`; the build note is `rust, cold`, then `rust, warm` |
| Debug build | `cstudy test --debug` builds with `--profile dev` instead of `--release`: `opt-level = 0`, `debug = true`, and the release profile's `overflow-checks`, `panic`, `strip` and `split-debuginfo`, pinned the same way (workspace manifest and `--config profile.dev.*`), so a debugger sees every line and variable. The first debug build compiles the runner crates again; before it the CLI prints `compiling the Rust runner for debugging (first debug run)` ([debug mode](#debug-mode)) |
| Editor project | `rust/Cargo.toml` lists each started problem as an `[[example]]` with `crate-type = ["lib"]` ([layout](installation-and-workspaces.md#layout)) and has `rust_decimal` and `chrono` as dev-dependencies; `rust/.cargo/config.toml` points crates.io at the runtime's vendored crates, for the `cargo` commands rust-analyzer runs in `rust/`. The build reads neither |
| Never | `ref_of` or `as: index` on a `ListNode` (`load_error` `UnsupportedType`) and cyclic list inputs (`InvalidInput`): an `Option<Box<ListNode>>` has one owner per node. [S13](authoring.md#static) keeps `rust` out of such problems |

## Request file

```json
{
  "protocol": 1,
  "mode": "test",
  "jobs": [
    {
      "job_id": "two-sum",
      "kind": "function",
      "target": {"path": "/home/me/ws/python/practice/two_sum.py"},
      "names": {"function": "two_sum", "params": {"nums": "nums", "target": "target"}},
      "signature": {"function": {"name": "twoSum", "params": [{"name": "nums", "type": "int[]"}, {"name": "target", "type": "int"}], "returns": {"type": "int[]"}}},
      "cases": [
        {"id": "ex1", "input": {"nums": [4, 9, 2, 7], "target": 11}}
      ]
    }
  ]
}
```

| Field | Notes |
|-------|-------|
| `mode` | `test` or `bench` ([Bench mode](#bench-mode)) |
| `kind` | The problem's kind, or `suite` for a project's native tests ([Project jobs](#project-jobs)) |
| `target` | Python and TypeScript: `{"path": <abs file>}`. JVM: `{"class": "practice.two_sum.Solution"}` (classpath from the command line). Go and Rust: `{"compiled": "user"}` or `{"compiled": "ref/<approach>"}`, the id of code built into the runner binary, since compiled code has no file or class to load. A Python project: `{"project": <abs root>, "module": <dotted entry module>}` ([Project jobs](#project-jobs)) |
| `names` | Language-specific symbol names computed by the CLI from the naming rules; runners do no name conversion. Class kinds: `{"class": "LRUCache", "methods": {"get": "get", "put": "put"}}`; Go and Rust add `"constructor"` (`NewLRUCache` and `new`), the function that creates an instance, with Go methods exported (`"get": "Get"`). The Rust runner reads neither `names` nor `signature`: its bridge was generated from them |
| `signature` | Canonical signature from `meta.yaml`, including modifiers; drives deserialization and serialization |
| `cases` | Inputs only. Function kind: `input`. Class kinds: `ops`, `args` |

## Locating user code

| Runner | Function kind | Class kinds |
|--------|---------------|-------------|
| Python | `importlib.util.spec_from_file_location(<unique module name>, path)`, then `getattr(module, names.function)` | `getattr(module, names.class)` |
| TypeScript | `await import(pathToFileURL(path).href)`, then the named export | named export class |
| JVM | `Class.forName(target.class)`, new instance via no-arg constructor, then the public method with `names.function` and the arity from the signature, parameter types matched against the mapping table | constructor with matching arity and types; methods by name and arity |
| Go | `names.function` in the target's generated registration; its `reflect` type must equal the [Go mapping](problem-format.md#go-and-rust-mapping) exactly | `names.constructor` in the registration, then each method by `MethodByName` on its result (exported names only), types checked the same way, when the job loads; calls go through the [generated thunks](#go-build-details) |
| Rust | The generated bridge calls `<module>::<function>` with every argument's type spelled, so the compiler checks the [Rust mapping](problem-format.md#go-and-rust-mapping) | `<module>::<Class>::new`, then each method through a `match` on the operation name in the bridge |

A missing file, import or compile failure, missing symbol or arity mismatch produces a `load_error` event for the job. In Go a missing symbol is a compile error of the generated registration (and a method with other parameters one of the generated thunk file, which is left out and checked by reflection instead), and in Rust a missing symbol or another signature is a compile error of the generated bridge; the CLI builds again without it and the runner reports it ([Go build details](#go-build-details), [Rust build details](#rust-build-details)).

## Node modifiers

How runners apply the node modifiers of [problem-format](problem-format.md#modifiers):

| Item | Rule |
|------|------|
| Traversal order | Every node reachable from the parameter, each once (cycles allowed): `ListNode` in list order from the head; `TreeNode` in level order (breadth-first, left child before right, null children skipped); `GraphNode` breadth-first from the given node, neighbors in adjacency-list order |
| `ref_of: <param>` | The first node of `<param>` in traversal order whose `val` equals the JSON value |
| `as: index`, `of: <param>` | The traversal order of `<param>` is taken before the call; the result serializes as the returned node's position in it, compared by identity (`-1` for null). A returned node that is not a node of `<param>` (for example a newly built one) is `invalid_output` with reason `the returned node is not a node of "<param>"` |
| Identity in Rust | A node's address: the `Rc` of a tree or graph node, the `Box` of a list node. `ref_of` hands the function a clone of the node's `Rc`, so it is defined for trees and graphs only. The call runs with freed memory retained, so a node created during the call never takes the address of one the parameter held, even one the function dropped |

## Execution environment

| Concern | Python | TypeScript | JVM | Go | Rust |
|---------|--------|------------|-----|----|------|
| Deep recursion | cases run in a worker thread created after `threading.stack_size(256 MiB)`; `sys.setrecursionlimit(10**6)` | Node default stack; content keeps depth at or under 3000 | cases run in a `Thread` with 256 MiB stack size | cases run on the main goroutine, whose stack grows on demand up to Go's 1 GB limit | cases run on a thread named `cs-runner-cases` with a 256 MiB stack; a stack overflow aborts the process (a crash) |
| Output capture | `contextlib.redirect_stdout` / `redirect_stderr` per case | replace `console.log/info/warn/error` and wrap `process.stdout.write` per case | `System.setOut` / `System.setErr` per case | file descriptors 1 and 2 are redirected to one pipe per case with `dup2`, because the `println` builtin writes to fd 2 directly; `debug.SetCrashOutput` (Go 1.23) still sends a fatal error to the real standard error | file descriptors 1 and 2 are redirected to one pipe per case with `dup2`, and `io::stdout()` is flushed before they are restored, because `print!` is buffered and the standard library's capture is unstable |
| Output limit | Standard output and standard error share one buffer that keeps the first 4096 bytes of UTF-8, never splitting a character; when anything was dropped, the runner appends exactly `\n[output truncated at 4 KiB]\n` | same | same | same | same |
| Fresh inputs | deserialize per case (and per bench repetition) | same | same | same | same |
| Node classes | duck-typed field access, never `instanceof` | same | `cs.support` classes | `cstudy/support` types (`*support.ListNode`, through the stubs' aliases): types must match exactly | `cs_support` types (`Option<Box<ListNode>>`, `Option<Rc<RefCell<TreeNode>>>`, `Option<Rc<RefCell<GraphNode>>>`), checked by the compiler in the bridge |
| Decimal and date output | `decimal` must be a finite `Decimal` and is written as `format(value, "f")` without trailing fractional zeros (`-0` as `0`); `date` must be a `date` that is not a `datetime`, written by `isoformat()`. Anything else, `float` and `int` included, is `invalid_output` | `decimal` must be a `Decimal` from `#support`, recognized by its `unscaled` and `scale` fields, written the same way; `date` must be a `YYYY-MM-DD` string naming a real day | `decimal` must be a `BigDecimal`, written by `stripTrailingZeros().toPlainString()` (`0` for zero); `date` must be a `LocalDate` in years 0001 to 9999. `null` and other classes are `invalid_output` | `decimal` is a `decimal.Decimal`, written from its coefficient and exponent without trailing fractional zeros (`0` for zero), whatever the package settings `TrimTrailingZeros` and `UseScientificNotation` say; `date` must be a `time.Time` in `time.UTC` at midnight, in years 0001 to 9999. Another location, a time of day or a year outside that range is `invalid_output` | `decimal` is a `rust_decimal::Decimal`, written by `normalize()` and `Display` (no trailing fractional zeros, `-0` as `0`, never an exponent); an input that does not fit it, more than 28 digits after the point or a magnitude of 2^96 or more, is `InvalidInput`. `date` is a `chrono::NaiveDate`; a year outside 0001 to 9999 is `invalid_output`. The compiler checks both types in the bridge |
| Decimal context | every case starts with a fresh `decimal.Context()` (precision 28, `ROUND_HALF_EVEN`), so a solution that changes the context cannot affect a later case | none | none | every case starts with shopspring/decimal's default package settings (`DivisionPrecision` 16 and the rest), so a solution that changes one cannot affect a later case or another target | none |
| Exit from user code | `SystemExit` caught as case error | `process.exit` is replaced with a throwing stub | `System.exit` cannot be blocked on Java 21; the CLI reports the runner exit as a crash on the current case | `os.Exit` cannot be blocked: reported as a crash, as on the JVM | `std::process::exit` cannot be blocked: reported as a crash |

## Event stream (`--out`, JSON Lines)

Each line is flushed immediately so the CLI can follow progress.

```json
{"event": "hello", "runner": "python", "protocol": 1, "runtime": "3.13.2"}
{"event": "job_start", "job_id": "two-sum"}
{"event": "case_start", "job_id": "two-sum", "case_id": "ex1"}
{"event": "case_result", "job_id": "two-sum", "case_id": "ex1", "status": "ok", "output": [1, 2], "duration_ns": 41000, "stdout": ""}
{"event": "case_result", "job_id": "two-sum", "case_id": "h1", "status": "error", "error": {"type": "IndexError", "message": "list index out of range", "trace": "two_sum.py:7 in two_sum"}, "duration_ns": 12000, "stdout": ""}
{"event": "job_end", "job_id": "two-sum"}
{"event": "bye"}
```

| `case_result.status` | Meaning |
|----------------------|---------|
| `ok` | Target returned; `output` holds the serialized value (class kinds: one entry per op) |
| `error` | Target threw; `error` holds type, message and a trace filtered to user frames (max 10 lines). Class kinds add `op_index` and `partial_output` |
| `invalid_output` | Return value cannot be serialized as the declared type (wrong type, cycle, too long, alias violation, non-finite double, a `decimal` or `date` that is not one, see [Execution environment](#execution-environment)) with a `reason` |
| `stalled` | Concurrent stress runs only: workers still unfinished at the run deadline ([Concurrent jobs](#events)) |
| `failed`, `skipped` | Suite jobs only: an assertion failed, or the framework skipped the test ([Suite job](#suite-job)) |

Every `case_result` carries `duration_ns`; `stdout` and `error.trace` may be omitted when empty.

`load_error` replaces all `case_*` events of a job: `{"event": "load_error", "job_id": ..., "error": {...}}`.

`duration_ns` measures only the call (and serialization is excluded), using `time.perf_counter_ns`, `process.hrtime.bigint()`, `System.nanoTime()` or `std::time::Instant`. Rust panics carry a message and no type, so their `error.type` is `panic`; the trace keeps the frames in the target's file, and in a release build the panic's own location stands in for a function inlined without one.

## Runner exit codes

| Code | Meaning | CLI handling |
|------|---------|--------------|
| 0 | Protocol completed (`bye` written), regardless of case outcomes | Read events |
| 2 | Bad request (unknown protocol version, invalid JSON), while no case is in progress | Internal error, CLI exits 70 |
| 3 | Restart requested after a stress run left threads alive (only after a `restart_requested` event) | Restart for the remaining cases without using up the crash-restart budget ([Concurrent jobs](#exit-codes-hang-guard-and-restarts-additions)) |
| other | Crash: any exit without `bye`, including 0 or 2 during a case, and 3 without a preceding `restart_requested` | Report crash on the case in progress (or the next case not run yet) with the last 20 stderr lines; restart for remaining cases |

## Hang guard and restarts

The CLI watches the event file:

| Phase | Limit | On expiry |
|-------|-------|-----------|
| Until `hello` | 5 s (Python, TypeScript, Go, Rust), 15 s (JVM) | Environment error, exit 4 |
| `case_start` to `case_result` | config `hang_guard.ms` if set, else case `hang_guard_ms`, else meta `limits.hang_guard_ms`, else 10000 | Kill the process group; case status `timeout`; restart the runner with the remaining cases |
| Any other gap between events after `hello` (for example loading user code) | 10000 | As above, reported on the next case not run yet |
| `case_start` to `case_result` of a concurrent stress run | `deadline_ms + 5000` | As for other cases |

After 3 restarts in one run, remaining cases are reported `not_run`. The hang guard is always on, except in [debug mode](#debug-mode), and is independent of optional time limits ([performance-analysis](performance-analysis.md#time-limits)).

## Debug mode

`cstudy test --debug` ([cli](cli.md#cstudy-test)) starts the runner under its language's debug agent, so an IDE can attach to the real runner that judges the code and stop at breakpoints in the user's file. The request, the events and the verdicts are the normal ones; only the way the runner starts and the watchdog change. The agents listen on `127.0.0.1` only.

| Runner | Agent (default port) | Added to the [invocation](#invocation) | Ready when it prints |
|--------|----------------------|----------------------------------------|----------------------|
| Python | debugpy from the workspace venv (5678) | `python -X frozen_modules=off -c <bootstrap> <port> --request R --out O`. The bootstrap runs `debugpy.listen(("127.0.0.1", port))`, prints `cstudy-debug-agent-listening` to standard error, calls `debugpy.wait_for_client()`, then runs `cs_runner` through `runpy` as `-m cs_runner` would | `cstudy-debug-agent-listening` on standard error |
| TypeScript | Node inspector (9229) | `node --inspect-wait=127.0.0.1:<port> runner.ts ...`; Node keeps the line and column of the `.ts` file | `Debugger listening on` on standard error |
| Java, Kotlin | JDWP (5005) | `java ... -agentlib:jdwp=transport=dt_socket,server=y,suspend=y,address=127.0.0.1:<port> -cp ...` | `Listening for transport dt_socket` on standard output |
| Go | Delve (2345) | `dlv exec --headless --listen=127.0.0.1:<port> --api-version=2 <binary> -- --request R --out O`, with the [debug build](#go-build-details) of the runner. Delve holds the runner at its entry point until the IDE continues it | `API server listening at:` on standard output |
| Rust | `debugserver` on macOS, `lldb-server gdbserver` on Linux (12345) | `debugserver --named-pipe <ready file> 127.0.0.1:<port> -- <binary> --request R --out O` (`lldb-server gdbserver --named-pipe ...` on Linux), with the [debug build](#rust-build-details) of the runner. The server holds the runner at its entry point until the IDE connects with `gdb-remote` and continues it. The ready file is `debug-port` in the launch's private directory, created empty before the launch: `--named-pipe` also takes a regular file, and the server writes only to one that exists | The ready file is no longer empty (the server wrote its port there): `debugserver` prints nothing |

| Item | Rule |
|------|------|
| Waiting | Every agent holds the runner before it reads the request, so no `hello` comes until the IDE attached and resumed it. Cases run on the thread named `cs-runner-cases` (Python, JVM, Rust) |
| Watchdog | None: no hello timeout, no hang guard, no idle limit. A runner paused at a breakpoint is not hung, and runners join the case thread without a timeout in test mode. `duration_ns` includes the time spent paused, so `cstudy test --debug` shows no durations and applies no time limit |
| Restarts | None. A crash, including an IDE that ends the session, is reported on the case in progress as usual and the remaining cases are `not_run` (`the runner ended during the debug session; it is not restarted`). A runner that ends before `hello` is an environment error (exit 4) that shows the runner's last output lines |
| Output | Standard output is kept next to standard error in `.cs/runs/<run_id>/stdout-<n>.txt`, because the JVM agent announces itself there. Normal runs send it to `/dev/null` |
| Ready line | `cstudy` reports the [ready line](cli.md#debugging) once, after it saw the ready text above in the runner's output, so the agent is bound when the IDE sees it. A runner that finishes without ever listening (Node continues without its inspector when the port is taken) is an environment error |
| Port | Before building, `cstudy` binds the port on `127.0.0.1` and releases it again to see that it is free; it never connects to it, since an IDE could take the connection for its debuggee. A port in use is an environment error that names the port and `--debug-port` |
| Python agent | `debugpy` missing from `python/.venv` is an environment error with the fix `uv add --dev debugpy --directory python` (the workspace template lists it, so `cstudy doctor --fix` installs it in new workspaces; `cstudy doctor` warns when it is missing) |
| Delve | Looked up on PATH, then where `go install` puts it: `GOBIN`, or `bin` of the first `GOPATH` entry (`~/go/bin` by default). Missing, it is an environment error that names it and how to install the tested release, before anything is built: ``cannot debug go: dlv was not found; run `go install github.com/go-delve/delve/cmd/dlv@v1.27.2` (<toolchains guide>#go)``; `cstudy doctor` warns when it is missing. On macOS Delve runs the runner through Xcode's `debugserver`, so it also needs the Command Line Tools. It runs without `--accept-multiclient`: when the IDE disconnects, Delve ends the runner and exits, so the case in progress is reported as a crash, as for an IDE that ends any session |
| Rust's debug server | macOS: `debugserver` from `LLDB_DEBUGSERVER_PATH`, PATH, or the `LLDB.framework` of the selected developer directory (`DEVELOPER_DIR`, else `xcode-select -p`: an Xcode's `SharedFrameworks`, or the Command Line Tools' `PrivateFrameworks`), as `lldb` itself finds it. Linux: `lldb-server` on PATH. Missing, it is an environment error before anything is built: ``cannot debug rust: debugserver was not found; run `xcode-select --install` (<toolchains guide>#rust)``, or ``lldb-server was not found; install your distribution's lldb package``; `cstudy doctor` warns when it is missing. macOS asks for permission to debug unless the user is in the `_developer` group or developer mode is on (`DevToolsSecurity -enable`) |
| Stopping | Ctrl-C, SIGTERM and SIGHUP (what an IDE sends when its task is stopped) kill the runner's process group, so a stopped run never leaves the debug port held. When a debug run ends, however it ends, every process still running a file of the launch's private directory (`scratch`: the copy of the compiled runner, for Go and Rust) is killed too, by executable path and not by group. A debug server that lets go of its runner (`debugserver` after lldb's `detach`, which is how CodeLLDB ends an attach session) exits and leaves the runner going, followed by nobody and without a time limit; `debugserver` starts the runner in a process group of its own, so the group of the server's process never reaches it. A case still in progress is reported as a crash. VS Code's CodeLLDB configuration also ends the runner with the session (`preTerminateCommands`: an lldb `script` that kills the process only while it is alive) |
| Scope | One language per run, the one of the attempt. Not with `--watch`, `--perf`, `--stress`, `--seed`, `--json` or `--time-limit`. A concurrent problem runs its sequential cases only: stress runs have deadlines that a paused runner would fail. A debug run is judged and shown but not stored |

### Connecting to the IDE (JVM)

`--debug-connect` replaces `server=y` with `server=n`: the JVM connects to an IDE that already listens on the port (IntelliJ's "Remote JVM Debug" in "Listen to remote JVM" mode) instead of listening for it. `cstudy` prints its ready line as it starts the JVM, because nothing binds a port on its side.

| Item | Rule |
|------|------|
| Nobody listening | The JVM exits with code 2 and prints `transport error 202: connect failed` on standard error (and `AGENT_ERROR_TRANSPORT_INIT(197)`). `cstudy` recognizes the first text, whatever the exit code, and launches the JVM again |
| Retries | After 0.2 s, then doubling up to 1 s between launches, for up to 10 s from the first launch; each launch rewrites the files of the same attempt and the ready line is not repeated |
| Giving up | Exit 4: `no debugger listening on 127.0.0.1:<port>; start the IDE's 'Debug JVM (listen)' configuration first` |
| Port check | None: the IDE is expected to hold the port |
| Any other end | A JVM that exits before `hello` for another reason is not launched again: an environment error with its last output lines |

## Bench mode

The request carries one job per problem with several targets, so all targets share one process, one runtime and the same inputs.

```json
{
  "protocol": 1,
  "mode": "bench",
  "jobs": [
    {
      "job_id": "two-sum",
      "kind": "function",
      "signature": {},
      "targets": [
        {"target_id": "user", "target": {"path": "/home/me/ws/python/practice/two_sum.py"}, "names": {"function": "two_sum"}, "output": true},
        {"target_id": "brute-force", "target": {"path": "/home/me/ws/.cs/build/python/ref/two_sum/brute_force.py"}, "names": {"function": "two_sum"}},
        {"target_id": "hash-map", "target": {"path": "/home/me/ws/.cs/build/python/ref/two_sum/hash_map.py"}, "names": {"function": "two_sum"}, "output": true}
      ],
      "inputs": [{"size": 100, "input": {}, "max_batch": 10000}, {"size": 1000, "input": {}, "max_batch": 1000}],
      "settings": {"reps": 7, "warmup": {"min": 1, "max": 1, "cv": 0.05}, "budget_ms": 2000, "memory": true, "min_sample_ns": 20000000}
    }
  ]
}
```

`signature` and the `input` objects are elided above. Class kinds give each input as `ops` and `args` instead of `input`, like test cases.

| Field | Meaning |
|-------|---------|
| `targets[].output` | Optional, default false: report the output of each size's check call (`bench_output`). The CLI sets it on the user's code and on the reference it compares the user's output with |
| `inputs[].max_batch` | At most this many calls per timed sample. The CLI sends `min(100000, max(1, budget / elements))` with a budget of 10^6 input elements for Python and 10^7 for TypeScript, the JVM, Go and Rust, which bounds the decoded copies held at once. `elements` counts what one decoded copy holds: list items and object values recursively, string characters, and 1 per other scalar (at least 1), so an input of one integer is not capped by its value |
| `settings.warmup` | Warm up until the coefficient of variation of the latest 5 runs is at most `cv`, after at least `min` and at most `max` runs (the check call counts as the first), and stop early once the warmup has taken `budget_ms` of wall time (decoding and collection included), so slow calls and large inputs do not warm up for 20 runs. The CLI sends `{1, 1}` for Python, `{3, 20}` for TypeScript, `{5, 20}` for the JVM and `{1, 3}` for Go and Rust ([measurement](performance-analysis.md#measurement)) |
| `settings.min_sample_ns` | Calls shorter than this are batched: one sample makes `calls` back-to-back calls, each on its own freshly decoded input, so that it lasts at least this long. The CLI sends 20000000 (20 ms): shorter samples were too noisy on a busy machine |

Per size, in request order:

1. Each target makes one **check call** through the test-mode path. A thrown exception or an unserializable result emits `bench_error` and the target stops; a call over `budget_ms` emits `bench_budget_exceeded` and the target stops. Output targets emit `bench_output`.
2. Each target **warms up** with samples until settled, growing its batch until a sample lasts `min_sample_ns`.
3. **Timed repetitions**: `reps` rounds, targets round-robin within each round, so drift and thermal effects spread across targets. Every sample emits `bench_sample`; a call over the budget stops the target as above.
4. With `memory`, each target makes one **memory call** (`bench_memory`), measured as in [performance-analysis](performance-analysis.md#measurement).

Inputs are deserialized fresh before every call, outside the timed region; results stay referenced until the sample ends, so freeing them is not timed either. Node is started with `--expose-gc` in bench mode. User output is not captured in timed calls (the runner's standard output is discarded).

```json
{"event": "bench_start", "job_id": "two-sum", "target_id": "hash-map", "size": 1000}
{"event": "bench_output", "job_id": "two-sum", "target_id": "hash-map", "size": 1000, "output": [17, 803]}
{"event": "bench_sample", "job_id": "two-sum", "target_id": "hash-map", "size": 1000, "rep": 3, "wall_ns": 880000, "cpu_ns": 870000, "calls": 10}
{"event": "bench_memory", "job_id": "two-sum", "target_id": "hash-map", "size": 1000, "metric": "tracemalloc_peak", "bytes": 73728}
{"event": "bench_budget_exceeded", "job_id": "two-sum", "target_id": "brute-force", "size": 100000, "wall_ns": 5120000000}
{"event": "bench_error", "job_id": "two-sum", "target_id": "user", "size": 1000, "status": "error", "error": {"type": "IndexError", "message": "list index out of range"}, "duration_ns": 41000}
{"event": "load_error", "job_id": "two-sum", "target_id": "user", "error": {"type": "ImportError", "message": "..."}}
```

| Event | Meaning |
|-------|---------|
| `bench_start` | A call, or a batch of calls, of this target at this size is about to run; precedes every check, warmup, timed and memory call |
| `bench_output` | The check call's serialized output |
| `bench_sample` | `wall_ns` and `cpu_ns` cover all `calls` calls of the sample (default 1); the time per call is their quotient |
| `bench_memory` | One memory figure per target and size |
| `bench_budget_exceeded` | One call took `wall_ns`, more than `budget_ms`; the target is not run at this or larger sizes |
| `bench_error` | `status` `error` or `invalid_output` with the fields of a `case_result`; the target stops |
| `load_error` | With `target_id`: that target did not load; the job's other targets still run |

Hang guard in bench mode: after a `bench_start`, the gap to the next event may last the job's hang guard, `max(hang guard, budget_ms)` with the hang guard resolved as for cases (config, then meta, then 10000). On expiry the CLI kills the runner, records a call over the budget for that target at that size, and restarts the runner at that size with the targets still running, which are measured afresh there. A crash is recorded as that target's failure instead. After 3 restarts the bench stops early and says so. Per-language measurement details are in [performance-analysis](performance-analysis.md#measurement).

## Concurrent jobs

Format and verdict rules: [problem-format](problem-format.md#concurrent-problems). Everything here is additive to protocol 1: existing jobs, events and exit codes keep their meaning, and `protocol` stays `1`.

### Capability

`hello` gains `"features": ["stress"]` in runners that implement this section. If a request contains a `concurrent` job and the `hello` lacks `stress`, the CLI kills the runner and exits 4 (`runner <lang> does not support concurrent problems`). `cstudy doctor` prints the features after the protocol (`protocol 1, stress`).

### Request

The CLI expands every (stress case, variant, run) into one request case, so the runner only executes literal scripts.

```json
{
  "job_id": "bounded-blocking-queue",
  "kind": "concurrent",
  "model": "threads",
  "target": {"class": "practice.bounded_blocking_queue.BoundedBlockingQueue"},
  "names": {"class": "BoundedBlockingQueue", "methods": {"put": "put", "take": "take", "size": "size"}},
  "signature": {},
  "cases": [
    {"id": "ex1", "ops": ["BoundedBlockingQueue", "put", "take"], "args": [[2], [5], []]},
    {"id": "s1:platform:0", "stress": {
      "seed": 1000,
      "thread_kind": "platform",
      "deadline_ms": 5000,
      "perturb": {"yield_probability": 0.05, "max_yields": 3, "python_granularity": "line"},
      "setup": {"ops": ["BoundedBlockingQueue"], "args": [[4]]},
      "workers": [
        {"ops": ["put", "put"], "args": [[0], [1]]},
        {"ops": ["take", "take"], "args": [[], []]}
      ],
      "final": {"ops": ["size"], "args": [[]]}
    }}
  ]
}
```

| Field | Notes |
|-------|-------|
| `kind` | `concurrent`; `names` and `signature` as for class kinds |
| `model` | `threads` or `async`. A runner that cannot run the model (TypeScript `threads`, JVM `async`) treats the request as bad (exit 2) |
| case `id` | Sequential cases keep their id. Stress runs are `<case_id>:<variant>:<run>`, for example `s1:virtual:7`; runners echo ids and never parse them |
| `stress.seed` | Already `seed + run`; seeds the per-worker PRNGs |
| `stress.thread_kind` | JVM only: `platform` or `virtual` |
| `stress.workers` | Fully expanded scripts; a worker's ordinal is its position in this array. Ops may be harness ops (`@enter`, `@exit`, `@pause`) |
| `stress.final` | Optional; no constructor |

Case order: sequential cases, then stress cases in file order, then variant (`platform` before `virtual`), then run index. After a restart the CLI writes the remaining cases to the next `request-<n>.json` as usual.

### Run procedure

Every stress run is independent: fresh argument decoding, a fresh instance, fresh probe sections and fresh PRNGs.

| Step | Action |
|------|--------|
| 1 | Decode every argument of setup, workers and final, outside the timed region |
| 2 | Start output capture: one buffer per run shared by all workers (thread-safe), same 4 KiB rule as other cases |
| 3 | Run `setup` sequentially on the case thread (async: inside the run's event loop). A throw or unserializable result ends the run: `error` or `invalid_output` with `phase: "setup"` and `op_index` |
| 4 | Create every worker with its PRNG; each waits at the start gate. When all wait, record the start time and open the gate |
| 5 | Each worker, per op: maybe yield ([Perturbation](#perturbation)); mark the op as in progress; call it (harness ops natively); encode the result immediately on the worker; record it |
| 6 | The coordinator waits until every worker finished, one failed, or `deadline_ms` passed since the gate opened |
| 7a | All finished: run `final` sequentially; status `ok` |
| 7b | First worker failure (throw or unserializable result): stop waiting; JVM interrupts the other workers, async cancels them, Python threads, Go and Rust leave them; status `error` or `invalid_output` with `phase: "worker"`, `worker`, `op_index`, `progress` |
| 7c | Deadline passed: status `stalled` with `progress`; the JVM interrupts the unfinished workers as in 7b |
| 8 | Restore perturbation settings, stop capture, write `case_result` |
| 9 | Threads model: if any worker thread (in Go, a worker goroutine) is still running 200 ms later, write `restart_requested` and exit 3 |

`duration_ns` of a stress run is the time from gate open to the last worker finishing (or the failure or deadline); setup and final are excluded.

Details the procedure settles:

| Item | Rule |
|------|------|
| After 7b or 7c | Every runtime sets a stop flag that workers check before each op, so a worker that is not stuck inside user code ends at its next op boundary. Python and Rust threads and goroutines cannot be stopped otherwise; TypeScript promises cannot be cancelled, so an unfinished worker's pending promise is abandoned |
| Failures after the decision | The first failure wins; failures reported after the coordinator decided (for example an `InterruptedException` caused by the harness interrupt) are dropped |
| `progress` | Lists every unfinished worker, the failing one included |
| Decoding errors | An argument that does not decode fails the run before setup with `error` (type `InvalidInput`) in the phase that holds the op |
| Python perturbation | The switch interval and monitoring apply from just before the workers start until they finished, failed or passed the deadline; setup and the final sequence run without them, and only worker threads draw yields |
| JVM coordinator | Waits on one monitor for "all finished or one failed" with the remaining time, which is equivalent to joining each worker |
| Go coordinator | Waits for a channel that is closed once every worker finished or the first one failed, or for a timer at the deadline. Each worker goroutine closes a channel of its own when it returns, however it returns, and step 9 waits for those |
| Rust coordinator | Waits on a `Condvar` for "all finished or one failed" with the remaining time, like the JVM. Each worker thread counts itself as exited when it returns (a drop guard, so a panic counts too), and step 9 waits on the same `Condvar` for that count |
| Python `async` | Leaves no threads, so it never asks for a restart; a task that suppresses cancellation is caught by the hang guard |

### Per-runtime execution

| Concern | JVM (Java, Kotlin) | Python, `threads` | Python, `async` | TypeScript, `async` |
|---------|--------------------|-------------------|-----------------|---------------------|
| Worker | `platform`: `new Thread(null, r, "cs-worker-<ordinal>", 0)`, daemon. `virtual`: `Thread.ofVirtual().name("cs-worker-<ordinal>").unstarted(r)` | `threading.Thread(daemon=True)`, created after `threading.stack_size(16 MiB)`, restored afterwards | `asyncio.Task` in a fresh loop per run (`asyncio.run` on the case thread); setup and final run in the same loop | one async function per worker on the runner's loop |
| Start gate | `CountDownLatch` `ready(n)` then `go(1)` | `threading.Barrier(n + 1)` | `asyncio.Event`, set after every task is created | one shared promise, resolved after every worker started |
| Scheduler yield | `Thread.yield()` | `time.sleep(0)` | `await asyncio.sleep(0)` | `await new Promise((resolve) => setImmediate(resolve))` |
| Injection inside user code | none: true parallelism | `sys.monitoring` ([Perturbation](#perturbation)) | none | none |
| Calls | Reflection as for class kinds; an `InterruptedException` caused by the harness interrupt (7b) is not reported | Direct | Result awaited when `inspect.isawaitable` | Result awaited when it is a thenable |
| Deadline | Coordinator joins each worker with the remaining time | `Thread.join(remaining)` | `asyncio.wait(tasks, timeout=remaining)`, then cancel pending tasks | `Promise.race` against a `setTimeout`, cleared afterwards |
| Per-worker PRNG | `new SplittableRandom(seed * 1_000_003L + ordinal)` | `random.Random(seed * 1_000_003 + ordinal)` | same as threads | mulberry32 seeded with `(seed * 1000003 + ordinal) >>> 0` |

The compiled runners run the `threads` model only, with one variant, `thread` ([ADR 0012](../decisions/0012-go-and-rust.md)):

| Concern | Go | Rust |
|---------|----|------|
| Worker | One goroutine per worker; the scheduler runs them on up to `GOMAXPROCS` threads (the number of CPUs) | `std::thread::Builder` named `cs-worker-<ordinal>` with a 16 MiB stack, each holding an `Arc` of the instance |
| Start gate | A `sync.WaitGroup` of `n` that each worker marks ready, then one channel that the coordinator closes | `std::sync::Barrier` of `n + 1` |
| Scheduler yield | `runtime.Gosched()` | `std::thread::yield_now()` |
| Injection inside user code | none: true parallelism | none: true parallelism |
| Calls | Reflection as for class kinds, on the instance that setup created; a worker's panic is recovered in its own goroutine and reported like a case's | The bridge's `&self` calls on the shared instance; a worker's panic is caught on its own thread, whose panic record holds the trace |
| Deadline | `select` on the "decided" channel and a timer at the gate's opening plus `deadline_ms` | `Condvar::wait_timeout` with the remaining time |
| Per-worker PRNG | `math/rand/v2` PCG seeded with `(seed * 1_000_003 + ordinal, 0)` | SplitMix64 seeded with `seed * 1_000_003 + ordinal` (wrapping) |
| Stop | No goroutine can be stopped from outside: the stop flag ends a worker at its next op boundary, and one blocked or spinning in user code makes step 9 ask for a restart | The same for threads |

Sequential cases of a concurrent job run exactly like class-kind cases; in the `async` model each runs in its own event loop and awaitable results are awaited. Synchronous code that never yields (an infinite loop in the `async` model, or a busy loop that the deadline cannot interrupt) is caught by the CLI hang guard as `timeout`.

The PRNG streams need not match across languages; they only make each runtime's perturbation, and the whole `async` schedule, reproducible for a given seed.

### Perturbation

| Runtime | Between ops | Inside user code |
|---------|-------------|------------------|
| JVM | With probability `yield_probability`, `1 + nextInt(max_yields)` calls of `Thread.yield()` | none (no agent, no bytecode rewriting) |
| Python `threads` | Same rule with `time.sleep(0)` | See below |
| Go | Same rule with `runtime.Gosched()` | none: true parallelism |
| Rust | Same rule with `std::thread::yield_now()` | none: true parallelism |
| `async` (Python, TypeScript) | Same rule with macrotask yields | none: a monitoring callback cannot await |

Python `threads`, for the duration of each stress run only:

1. `sys.setswitchinterval(1e-5)`; the previous value is restored at step 8.
2. Unless `python_granularity` is `none`: `sys.monitoring.use_tool_id(3, "cs-stress")`, register one callback for `LINE` (granularity `line`) or `INSTRUCTION` (granularity `instruction`), `sys.monitoring.set_events(3, <event>)`, and `sys.monitoring.restart_events()` at run start.
3. The callback returns `sys.monitoring.DISABLE` for code whose `co_filename` is not the target file. In the target file, and only on worker threads (a `threading.local` flag), it draws from the worker's PRNG and with probability `yield_probability` calls `time.sleep(0)` `1 + randrange(max_yields)` times.
4. At run end: `sys.monitoring.set_events(3, 0)` and `sys.monitoring.free_tool_id(3)`.

### Harness ops

Each run has its own probe sections, created on first use. A section holds `shared`, `exclusive`, `entries`, `violations` and `max_occupancy`, guarded by a `synchronized` monitor (JVM), a `threading.Lock` (Python threads), a `sync.Mutex` (Go) or a `std::sync::Mutex` (Rust); the async runtimes need no lock.

| Op | Behavior |
|----|----------|
| `@enter [s, mode]` | Under the section lock: count a violation if `mode` is `exclusive` and `shared + exclusive > 0`, or `mode` is `shared` and `exclusive > 0`; then increment the mode's counter and `entries`, and raise `max_occupancy` to `shared + exclusive` |
| `@exit [s]` | Decrement the counter of the mode this worker last entered `s` with (per-worker stack). An `@exit` without a matching `@enter` is an `error` with type `HarnessError` |
| `@pause [n]` | `n` scheduler yields (the per-runtime yield above) |

### Events

```json
{"event": "hello", "runner": "jvm", "protocol": 1, "runtime": "21.0.2", "features": ["stress"]}
{"event": "case_result", "job_id": "bounded-blocking-queue", "case_id": "s1:platform:0", "status": "ok", "output": {"setup": [null], "workers": [[null, null], [0, 1]], "final": [0]}, "sections": {}, "duration_ns": 41000000, "stdout": ""}
{"event": "case_result", "job_id": "bounded-blocking-queue", "case_id": "s1:platform:1", "status": "error", "phase": "worker", "worker": 5, "op_index": 311, "error": {"type": "NoSuchElementException", "message": "", "trace": "BoundedBlockingQueue.java:31 in take"}, "progress": [{"worker": 0, "completed": 500, "in_op": false}, {"worker": 5, "completed": 311, "in_op": true}], "duration_ns": 9000000}
{"event": "case_result", "job_id": "bounded-blocking-queue", "case_id": "s2:platform:0", "status": "stalled", "progress": [{"worker": 0, "completed": 1203, "in_op": true}, {"worker": 3, "completed": 1202, "in_op": true}], "duration_ns": 5000000000}
{"event": "restart_requested", "reason": "2 worker threads still alive after s2:platform:0"}
```

| Field | On | Meaning |
|-------|----|---------|
| `output` | `ok` stress runs | `setup`, `workers` (one output array per worker, in request order, `null` for void and harness ops) and `final` (empty array when absent). The CLI joins it with the expanded scripts into the [run record](problem-format.md#run-record) |
| `sections` | `ok` stress runs | `{name: {entries, violations, max_occupancy}}`; `{}` when no probes ran |
| `phase` | `error`, `invalid_output` | `setup`, `worker` or `final` |
| `worker` | phase `worker` | Ordinal of the failing worker |
| `op_index` | `error`, `invalid_output` | Index in the phase's op list |
| `progress` | `error` (phase `worker`), `stalled` | Per worker: `completed` ops and whether it is inside op `completed` (`in_op`); finished workers may be omitted |
| `status: stalled` | new | Workers still unfinished at the deadline: deadlock, lost wake-up or livelock |

`restart_requested` (new event) is written only after a `case_result`, when leftover threads could disturb later runs; the runner then exits 3 without `bye`.

### Exit codes, hang guard and restarts (additions)

| Item | Rule |
|------|------|
| Exit code 3 | Written after `restart_requested`: the CLI restarts the runner with the remaining cases. These restarts do not count toward the limit of 3 crash restarts. `restart_requested` is only valid right after a stress run's `case_result` (anything else is a protocol error), so each stress run can cause at most one restart and the restarts of a request are bounded by its stress runs; there is no other cap. Settled against an earlier cap of 20 per `cstudy` invocation, which D7 alone can exceed: a lock-order deadlock reference is meant to stall in every run, and its threads stay blocked in `synchronized` (JVM) or in `Lock.acquire` (Python), so one problem can ask for 10 restarts per JVM variant and language plus 10 for Python |
| Shape check | A stress run's `ok` must report one output per op of setup, of every worker script and of final; otherwise the run is a protocol error |
| Stress `ok` | Recognized by its `sections` field; `phase` marks a stress `error` or `invalid_output` |
| Hang guard of a stress run | `deadline_ms + 5000` from `case_start`, replacing the other hang guard values; expiry is `timeout` and counts as a crash restart |
| Time limits | Never applied to stress runs |

### Broken reference materialization

Broken references are materialized next to the approaches ([Reference materialization](#reference-materialization)):

| Language | Location |
|----------|----------|
| Python | `.cs/build/python/ref/<snake_slug>/broken_<id_snake>.py` |
| TypeScript | `.cs/build/typescript/ref/<slug>/broken-<id>.ts` |
| Java, Kotlin | `.cs/build/jvm/<lang>/src/main/<lang>/ref/<snake_slug>/broken_<id_snake>/<ClassName>.<ext>`, package `ref.<snake_slug>.broken_<id_snake>` |
| Go | `.cs/build/go/ref/<snake_slug>/broken_<id_snake>/broken_<id_snake>.go` (named as in [Reference materialization](#reference-materialization)), a package of its own linked as target `ref/broken-<id>` |
| Rust | `.cs/build/rust/ref/<snake_slug>/broken_<id_snake>.rs`, the `#[path]` module `ref_broken_<id_snake>` |

### Conformance fixtures (Phase 5)

Added to `runners/conformance/` before any concurrent problem merges. `expectations.json` gains the outcomes `stalled` and `fail` (a completed run that broke an invariant or `final.expected`) and, for stress cases, `runs` plus `min_failed` or `max_failed`, `phase` for errors, `deterministic` and `restart_requested`; a fixture runs only in the languages its `meta.yaml` lists. Semantics: [runners/conformance/README.md](../../runners/conformance/README.md#outcomes).

| Fixture | Approaches | Expected |
|---------|------------|----------|
| `9014-conformance-stress-counter` | `atomic` (correct counter), `racy` (reads the count on one line and writes it on the next; TypeScript awaits between them) | `atomic` passes 10 of 10; `racy` fails at least 9 of 10 in every language and variant |
| `9015-conformance-stress-stall` | `never-opens` (`await` or wait on a gate nobody opens) | `stalled`, with `progress` naming the waiting workers |
| `9016-conformance-stress-worker-error` | `throws-at` (a worker op throws at op 100) | `error` with `phase: "worker"` and `op_index` 100 |
| `9017-conformance-stress-sections` | `locked`, `unlocked` (a mutex around `@enter`/`@exit` probes) | `locked`: 0 violations; `unlocked`: violations in at least 9 of 10 runs |
| `9018-conformance-stress-async-determinism` | `interleaves` (Python async, TypeScript) | Two runs with the same seed produce identical run records; different seeds produce at least two distinct records over 10 runs |
| `9019-conformance-stress-leak` | `ignores-interrupt` (threads: a worker spins forever after another worker throws) | `error`, then `restart_requested`; the next case still runs |

## Project jobs

A [project problem](problem-format.md#project-problems) is a folder, not one file, and its native tests run inside the runner. Two kinds of job serve it: a **grading job** (`cstudy submit`, and `cstudy verify` D1 and D3), an ordinary class job whose target is the project, and a **suite job** (`cstudy test`, and D1 and D9), which runs the project's native test framework in-process. The Python, TypeScript and JVM (Java and Kotlin) runners support both; the Rust runner does not support project jobs yet ([ADR 0014](../decisions/0014-project-problems.md)). The Go runner supports both too, running the tests as a child process ([Go project jobs](#go-project-jobs)).

### Capability

`hello.features` lists `project` and `suite` when the runner supports them. `cstudy` refuses a project job to a runner that does not list them, as an environment error (exit 4). The JVM runner lists `stress` and `project` always, and `suite` when a test framework host is on its classpath: a project's test runtime classpath holds `cs.suite`, the classpath of a single-file problem does not.

### Launch

| Item | Rule |
|------|------|
| Root | The project root: `projects/<slug>/` for the user's code, `.cs/build/projects/<slug>/<approach>/` for the reference |
| cwd | The root (`RunnerLaunch.cwd`), for both job kinds |
| Python command | The workspace venv's interpreter by path, `python/.venv/bin/python -P -m cs_runner --request R --out O`. `cstudy` never runs the venv's console scripts (`pytest`, `uv run pytest`), whose absolute shebangs break when the workspace moves. `-P` keeps the cwd off `sys.path`, so a user file named after a standard-library module or `pytest` cannot shadow it |
| Python environment | `PYTHONPYCACHEPREFIX=<workspace>/.cs/pycache`, so library and test bytecode never lands in the project and stays warm between runs, and `UV_NO_SYNC=1`, so nothing a project job starts lets uv sync, lock or delete the shared venv |
| TypeScript command | `node .cs/runtime/runners/typescript/runner.ts --request R --out O`, by absolute path, as for other jobs |
| Java and Kotlin command | After the folder's build ([JVM project builds](#jvm-project-builds)): `java -XX:+UseSerialGC -Xshare:auto -cp <classpath> cs.runner.Main --request R --out O`, the classpath being the build's main runtime classpath for a grading job and its test runtime classpath for a suite job, with the build's class directories and the runtime's jars replaced by the run's private copies |
| Isolation | One runner process per project job. Two projects may both define a top-level `bank` module, and a grading job and a suite job of one project would share `sys.modules`, so `cstudy verify` never batches a project job with another job |
| Debug | As for other jobs ([Debug mode](#debug-mode)): debugpy wraps `-m cs_runner` (with `-P`), which hosts pytest in the same process, `node --inspect-wait` runs the tests in the inspected process (`isolation: "none"`), and JDWP suspends the JVM that hosts the JUnit Platform, so breakpoints in the project's code and in its tests both stop. Grading jobs are never debugged: `cstudy submit` has no `--debug` |

### JVM project builds

A Java or Kotlin project folder is a Gradle build of its own ([starter](problem-format.md#starter)), which applies the `cs.project` plugin of the runtime's `runners/jvm` build: JDK 21, JUnit Jupiter for the tests and kotlin.test on JUnit 5 with Kotlin, `cs.runner` on the runtime classpath, and its JUnit Platform host `cs.suite` on the test runtime classpath ([ADR 0014](../decisions/0014-project-problems.md#java-and-kotlin-spike-k4)).

| Item | Rule |
|------|------|
| Command | `jvm/gradlew -p <root> -q --console=plain --offline <task>`, run in `jvm` like every JVM build, so it uses the workspace's Gradle and its daemon. `--offline`: a project build never reaches the network; `cstudy doctor --fix` caches what it needs |
| Tasks | A suite job builds `csClasspath`: the main and test classes, and both runtime classpaths, in `build/cs/main-classpath.txt` and `build/cs/test-classpath.txt`. A grading job builds `csMainClasspath`: the main classes and `build/cs/main-classpath.txt` only, so a test file that does not compile, such as a level's generated tests before its methods exist, never blocks a submission |
| Locked levels | `-Pcs.exclude=<path>,...` names the generated test files of the levels above `cstudy test --level N`, relative to the root, and the plugin leaves them out of the test compile: they may call methods that do not exist yet. The runner reads no `exclude` |
| Concurrent `cstudy` processes | One process at a time builds a folder and copies what it built: an exclusive `flock` on `.cs/build/jvm-locks/project-<folder name>-<digest of its absolute path>.lock`, held around the build, the read of the classpath file and the copy, with the runtime lock of [JVM build details](#jvm-build-details) inside it. Two folders, or a folder and a single-file problem, build side by side |
| Per-run class copy | As for single-file problems: the classpath entries below the folder's `build/` and the runtime's jars are copied into `.cs/build/jvm-runs/<pid>-<random>/`, which the run removes when it ends |
| Compile errors | Lines of the compiler's output that mention the folder's `src/`, with their indented context, at most 40: a grading job reports them as its `load_error` (type `CompileError`), so the submission is stored with every graded case errored and `cstudy submit` exits 2; a suite job reports them as the suite's `load_error`, and `cstudy test` lists them and exits 1 |
| Missing libraries | A build that fails because a library is not cached for offline mode is an environment error (exit 4): ``the project build needs libraries that are not cached yet; run `cstudy doctor --fix` once while online`` |
| Any other failure | An environment error with the last lines of Gradle's output |
| Cold start | As for other JVM builds, `warming Gradle daemon (first run)` before a build with no daemon running. The first build of a folder also configures it, 1.5 to 2.4 s on a warm daemon |

### Grading job

| Item | Python | TypeScript | Java and Kotlin |
|------|--------|------------|-----------------|
| `target` | `{"project": "<abs root>", "module": "bank.bank"}` | `{"path": "<abs root>/src/bank.ts"}`, launched in the root | `{"class": "bank.Bank"}`, the entry, as for single-file problems |
| Loading | The runner imports everything it needs first (`cs_runner`, `cs_support`, pytest for a suite job), then appends the root to the end of `sys.path` and imports `module` with `importlib.import_module`. Both `from .models import Account` and `from bank.models import Account` resolve | Relative imports resolve from each file's URL, under the project's `package.json` (`"type": "module"`). A bare import resolves only to Node's builtins: the project has no `node_modules` and no `#support` | `Class.forName` on the main runtime classpath, which holds the project's classes and the libraries it may use, never its tests or JUnit |
| Fresh code | Every module whose file is under the root compiles from source on every run, never from bytecode, as single files do (`_SourceOnlyLoader`), so an edit made within the same second is never hidden | Node reads the files on every run | Gradle compiles what changed, and the JVM loads the run's private copy |
| Signature | The request's `signature` and `names` hold only the methods with `level` at or below the graded level, so the load check of every declared method never asks for a method of a locked level | Same | Same |
| Missing entry | `load_error` `SymbolNotFound` naming the expected module and class (`bank.bank has no class Bank`) | `load_error` naming the file and the export | `load_error` `ClassNotFoundException` (`class bank.Bank not found`); code that does not compile is a `CompileError` ([JVM project builds](#jvm-project-builds)) |

Cases, events, the hang guard and restarts are those of every class job.

### Suite job

```json
{
  "job_id": "bank-project-python/suite",
  "kind": "suite",
  "framework": "pytest",
  "root": "/home/me/ws/projects/bank-project-python",
  "exclude": ["tests/test_level_2.py"],
  "select": [],
  "skip": []
}
```

| Field | Meaning |
|-------|---------|
| `framework` | `pytest`, `node-test`, `go-test` or `junit-platform` (Java and Kotlin) |
| `root` | The project root |
| `exclude` | Files, relative to the root, that are not run: the generated files of levels above `cstudy test --level N`. On the JVM the build has already left them out of the test compile |
| `select` | Test ids to run (`cstudy test --case`); empty: every test the framework discovers |
| `skip` | Test ids not to run, set on a restart |

A suite job has no `cases`: the framework discovers the tests. Python discovers them as pytest does from the root, under the project's `pyproject.toml` (`testpaths`, `pythonpath`, `addopts`); TypeScript takes the files `node --test` finds from the root with its default patterns; the JVM discovers them in every directory of its classpath, which are the project's main and test class directories, never in a jar.

| Item | pytest | `node:test` | `junit-platform` |
|------|--------|-------------|------------------|
| Host | `pytest.main([...])` on the `cs-runner-cases` thread, with `--rootdir <root>`, plugin autoloading off (`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`), `-p no:cacheprovider`, pytest's own capture off, and a plugin of the runner's that writes the events | `run({ files, isolation: "none", concurrency: 1 })` in the runner's process, its `test:start`, `test:pass` and `test:fail` events turned into protocol events | The JUnit Platform Launcher (`LauncherFactory.openSession()`) on the `cs-runner-cases` thread, with parallel execution off whatever a `junit-platform.properties` says, and a `TestExecutionListener` that writes the events. `cs.runner.Main` finds the host, `cs.suite`, with `ServiceLoader` |
| Test id | pytest's node id: `tests/test_level_1.py::test_ex1` | `<file relative to the root>::<test name>`, nested names from the outermost `describe` joined by ` > ` | `<class>::<method>`: `bank.Level1Test::ex1`, a nested class as `bank.Outer$Inner`, plus `[n]` per parameterized or dynamic invocation (`bank.RateTest::rounds[2]`). A class reported on its own is its class name |
| `skip` | Left out by exact node id in the runner's plugin (pytest's `--deselect` matches prefixes, so it is not used) | Left out by exact id: a `beforeEach` hook of the runner's throws before the body of a test that `skip` lists or `select` does not name, and nothing is reported for it (with isolation `none`, Node reads name patterns only from its own command line) | | Left out by exact id, and by class: every test of a class in `skip`, whose failed setup or skip was reported once under the class's id, so the setup does not run and report it again. A parameterized or dynamic test with an invocation in `skip` is left out whole, since running it again would report its earlier invocations a second time |

Events: `job_start`, then per test `case_start` and `case_result` with the test id as `case_id`, then `job_end`.

| `case_result.status` | When |
|----------------------|------|
| `ok` | The test passed |
| `failed` | It raised an assertion error (Python `AssertionError`, `node:assert`'s `AssertionError`, a JVM `AssertionError`): `message` holds the framework's failure text (pytest's assertion detail, such as `assert -1 == 5`; JUnit's `expected: <5> but was: <-1>`), plus `expected` and `actual` when the framework reports both: JSON values from `node:assert`, and on the JVM the strings opentest4j's `AssertionFailedError` carries (`"5"` and `"-1"`), which JUnit's `assertEquals` and kotlin.test's assertions both raise. pytest's `pytest.fail` and JUnit's `fail` count as `failed` |
| `error` | Any other exception, a setup or teardown failure, or a test file that fails to collect or import; `error` as for cases, the trace keeping the frames outside the JDK, Kotlin's library, JUnit and the runner. A collection failure is one result whose `case_id` is the file; pytest runs with `--continue-on-collection-errors`, so the other files still run. On the JVM a class whose `@BeforeAll` or `@AfterAll` fails is one result whose `case_id` is the class |
| `skipped` | The framework skipped it; `message` holds the reason. An expected failure (pytest `xfail`) is `skipped` with `message` `xfail: <reason>`. On the JVM a `@Disabled` test, or a disabled class reported once under its id, is `skipped` with JUnit's reason, and a failed assumption is `skipped` with `message` `aborted: <reason>` |

| Rule | Detail |
|------|--------|
| Output | Captured per test by the runner, as per case, with the 4 KiB limit ([Execution environment](#execution-environment)) |
| Hang guard | The case rules: from `case_start` to `case_result`, config `hang_guard.ms`, else meta `limits.hang_guard_ms`, else 10000; any other gap after `hello`, 10000. On expiry the process group is killed, the test is `timeout`, and the suite restarts with `skip` holding every test already reported and the one that hung |
| Crash | An exit without `bye` is reported on the test in progress, and the suite restarts the same way. After 3 restarts, tests not yet reported are `not_run`, and the report marks the suite as stopped early |
| No tests | A suite that discovers nothing ends with `job_end` and no results |
| Usage error | A framework usage or internal error that runs nothing (pytest `UsageError`, `InternalError`; on the JVM an exception from the Launcher before any test ran) is a `load_error` carrying the framework's output |
| Bytecode | Python: before each project run the CLI deletes the project folder's subtree of the bytecode prefix (`<ws>/.cs/pycache`), so an edit made within the same second that keeps the file size never runs stale code; the shared environment's bytecode stays cached |
| Judging | A suite result is the framework's verdict on code the user may edit: feedback, never a grade. No comparator runs on it, and no level opens from it |

### Go project jobs

The Go runner runs both project jobs from binaries that `cstudy` builds in `.cs/build/go` with the environment, lock, private copy and cold-start notice of [Go build details](#go-build-details); the tests themselves run in the test binaries of a `go test` that the runner starts ([ADR 0014](../decisions/0014-project-problems.md#go-spike-k5)).

| Item | Rule |
|------|------|
| `go.work` per root | `.cs/build/go/project/<root>/go.work`, where `<root>` is the project root relative to the workspace (`projects/bank-project-go`): `use` of the build module `csbuild` and of the root, and `replace` of the runner module `cstudy` and of each vendored module with the runtime's copies. A `replace` in a `go.work` outranks the folder's `go.mod`, so a reference's build copy, deeper than `projects/<slug>/`, builds too. Its `go` line is the higher of 1.24 and the folder's `go.mod` |
| Grading binary | `cmd/project/<snake_slug>/main.go` imports the entry's package as target `user`: `<module>/<directory of project.entry>`, or `<module>` for an entry at the root, with the module read from the root's `go.mod`. The registration (`New<Class>`) and the thunks of the graded levels' methods, generated in `.cs/build/go/project/<root>/`, enter that package through `go build -overlay`, so nothing is written to the folder. Built as `bin/project/<snake_slug>` with `GOWORK` naming the root's `go.work`, and launched in the root |
| Grading target | `{"compiled": "user"}` in a job of kind `project`, otherwise the class job of [Grading job](#grading-job) |
| Compile errors | Errors only in the registration or thunk files: the second pass and the runner's `load_error` of [Go build details](#go-build-details). Errors in the project's files: the binary is built again without the project, and the runner reports a `load_error` of type `CompileError` whose message is the compiler's lines with paths relative to the root (at most 40) and whose trace is the first error's `file:line`, so `cstudy submit` stores a submission whose code does not load and `cstudy verify` D1 and D3 name the errors. A failure with no diagnostics in the project is an environment error (exit 4), as for single files |
| Suite binary | `cmd/suite/main.go`, the runner with no target, built as `bin/suite/cs_go_suite`; the first suite build of a workspace also compiles `testing` and `testing/internal/testdeps`, so that a cold build cache does not keep the first `go test` silent past the CLI's idle limit. It is launched in the root with the fixed environment of [Go build details](#go-build-details), `GOWORK` naming the root's `go.work`, and `GOOS` and `GOARCH` set empty, which the go command reads as unset |
| Suite command | `go test -json -count=1 -timeout=0 [-overlay F] [-run R] [-skip S] ./...` in the root, a child process of the runner in the runner's process group: `-count=1` never reuses a cached result, `-timeout=0` leaves hangs to the hang guard, `F` maps each file of `exclude` to `""`, which removes it from the build, and `R` is `^(A\|B)$` of the top-level tests that `select` names |
| Test id | `<file>::<test>`: the file that declares the top-level test, relative to the root, which the runner finds by parsing the package's `_test.go` files, and the name `go test` reports, subtests included (`tests/level_1_test.go::TestEx1`, `bank_test.go::TestTransfer/too_big`). A package that does not build is reported under its import path (`bank-project-go/tests`) |
| `select` | A whole id or its last part (`TestEx1`, `TestTransfer/too_big`): `-run` names its top-level test, which runs with all its subtests; when every selection names a file, only those files' packages run |

| `go test -json` reports | `case_result` |
|-------------------------|---------------|
| `pass` | `ok`; `stdout` holds the test's output lines without the framing (`=== RUN`, `--- PASS`) |
| `fail` | `failed`; `message` holds the test's output lines without the framing: the `t.Error` and `t.Log` text with its `file:line:` prefix, or an Example's `got:` and `want:` lines. Every subtest is a test of its own, and a parent with a failed subtest fails too |
| `skip` | `skipped`; `message` is the skip reason |
| `build-output` and `build-fail`: a compile or `go vet` error | `error` of type `CompileError` on the package's import path, the message holding the errors with paths relative to the root, without the `#` headers; the other packages still run |
| A test binary that ends early: a panic, `os.Exit`, `log.Fatal` or a fatal runtime error such as a deadlock | `error` of the test it ended in: type `panic` or `fatal error` with the message and, as the trace, the frames in the project's files (`bank.go:14 in Bank.Deposit`, innermost last), or type `exit`; what the test printed before is its `stdout`. Its package then runs again |
| No event within the hang guard | A hang of the test still running |

| Rule | Detail |
|------|--------|
| Order | `go test` runs packages side by side and `t.Parallel` tests together, while the protocol has one test in progress, so the runner writes each test's `case_start` and `case_result` once the test ends, in the order tests end |
| Hang guard | When no `go test` event has arrived for 1 s, the runner writes `case_start` for a test still running: the earliest started one that has no unfinished subtest and is not paused (`t.Parallel` tests wait in `pause`). From there the CLI's hang guard applies to it as to any test, and the runner writes the results that end meanwhile after its own. So the guard times the gap since the last event, never a whole `run` to `pass` span, which a paused parallel test stretches |
| A binary that ends early | A test binary ended early when its package ends without the binary's own closing `PASS` or `FAIL` line and did not fail to build. The culprit is the test whose output holds a line starting with `panic: `, else the test still running in it. The runner reports the culprit's `error` and runs that package's `go test` again with `-skip` of its top-level tests reported so far, until a run ends normally, so a panic costs one more `go test` of its package and never a restart of the runner: a starter whose level 1 methods panic with `not implemented` reports every one of its tests. A binary that ended outside any test is an `error` of type `TestBinaryExited` on its package, which does not run again. A runner that ends while a test is in progress (`go test` itself was killed) is a crash, as for any runner |
| Restart | After a hang, `skip` holds the tests reported so far and the culprit; the runner turns it into `-skip` of their top-level tests, package by package. Each package with a skipped test runs in a `go test` of its own and the others run together, so a test that shares its name with one reported in another package still runs; a skipped package id leaves its package out. One regular expression cannot name an arbitrary set of subtests, so a restart, or a run again after a binary ended early, leaves out the whole top-level test of the culprit |
| No tests | A suite with no test file ends with `job_end` and no results |
| Usage error | A `go test` that fails before any package runs (a missing `go.mod`, a module it cannot resolve offline) is a `load_error` of type `GoTestError` carrying its output tail |
| Debug | `cstudy test --debug` runs one package under Delve: the package of the selections when they name files of one package, else the package of the generated test files (`project.tests`). The runner builds its test binary with `go test -c -gcflags=all=-N -l` into the launch's private directory, starts `dlv exec --headless --listen=127.0.0.1:<port> --api-version=2 --wd <package directory> <binary> -- -test.v=test2json -test.count=1 -test.timeout=0 -test.paniconexit0 [-test.run R] [-test.skip S]`, copies Delve's `API server listening at:` line to its own standard output for the [ready line](#debug-mode), and pipes the rest through `go tool test2json -t -p <import path>`. A package that does not build is reported as above, and nothing waits for a debugger; a test binary that ends early is reported as above and its package does not run again. Delve is found, and required, as in [debug mode](#debug-mode) |

### Not yet supported

Rust project jobs wait for spike K6, recorded in [ADR 0014](../decisions/0014-project-problems.md). Until then the Rust runner does not list `project` or `suite`, and check S14 keeps project problems out of Rust.

## Stub generation

| Step | Rule |
|------|------|
| Source | `StubGenerator` for the language renders the signature with the mapping table and naming rules from [problem-format](problem-format.md#type-dsl) |
| Destination | Python `python/practice/<snake_slug>.py`; TypeScript `typescript/practice/<slug>.ts`; Java and Kotlin `jvm/<lang>/src/main/<lang>/practice/<snake_slug>/<Solution or ClassName>.<ext>`; Go `go/practice/<snake_slug>/<snake_slug>.go` in `package <snake_slug>` ([Go file names](#go-file-names)); Rust `rust/practice/<snake_slug>.rs` |
| Body | Python `raise NotImplementedError`; TypeScript `throw new Error("Not implemented")`; Java `throw new UnsupportedOperationException("Not implemented")`; Kotlin `TODO("Not implemented")`; Go `panic("not implemented")`; Rust `todo!()`. Constructors are empty (Go: `return &LRUCache{}` from `NewLRUCache`; Rust: `LRUCache {}` from `pub fn new(...) -> Self`). Rust methods take `&mut self`, or `&self` in a concurrent problem, whose instance the worker threads share |
| Header | Title, statement path, run command |
| Imports | Support classes only when used (TypeScript `Decimal` for `decimal`, and the type `IsoDate` for `date`, imported with `import type` or an inline `type` specifier); the standard library types of `decimal` and `date` only when used (Python `Decimal` and `date`, Java and Kotlin `BigDecimal` and `LocalDate`); Java always `import java.util.*;`; Go imports `time` for `date`, `cstudy/support` for node types (with `type ListNode = support.ListNode` per node type used) and `github.com/shopspring/decimal` for `decimal`, each only when used since Go rejects unused imports, on one `import` line or in a block grouped as goimports groups it (paths without a domain first); Rust `use std::cell::RefCell;` and `use std::rc::Rc;` for trees and graphs, then one group in rustfmt's order of `use chrono::NaiveDate;` for `date`, `use cs_support::{...};` with the node types used, and `use rust_decimal::Decimal;` for `decimal` |
| Existing file | Kept unless `--fresh` or a review attempt; then archived to `.archive/<slug>/<attempt_id>-<lang>/` first |
| `stub: buggy` | Copy `problems/<dir>/buggy/solution.<ext>` instead of generating; buggy files declare no `package`, so on the JVM `cstudy start` prepends `package practice.<snake_slug>` (with `;` for Java). Go buggy files, like Go references, declare `package <snake_slug>` and are copied unchanged |
| Formatting | Generated text already matches ruff, Prettier defaults, Google Java style, ktlint defaults, gofmt and rustfmt (including its vertical layout for a signature over 100 characters); no formatter runs |
| Progressive | All methods emitted, each preceded by a `Level <n>` comment |
| Project | No stub: `cstudy start` copies the problem's `starter/` tree ([problem-format](problem-format.md#starter)) |
| Concurrent | `blocking` methods become async methods (async model) or declare `throws InterruptedException` (Java); Kotlin, Go and Rust declare them like any other method, since the call simply blocks its thread or goroutine; the header names the model ([problem-format](problem-format.md#stubs-for-concurrent-problems)) |

Every generated stub must compile or import unchanged; the conformance suite checks this for every DSL type.

## Reference materialization

`cstudy verify` and `cstudy bench` run references through the same runners by copying them into `.cs/build/<lang>/`:

| Language | Location | Adjustment |
|----------|----------|------------|
| Python | `.cs/build/python/ref/<snake_slug>/<approach_snake>.py` | none; executed with the workspace venv interpreter |
| TypeScript | `.cs/build/typescript/ref/<slug>/<approach>.ts` | `.cs/build/typescript/package.json` and `support.ts` mirror the workspace so `#support` resolves |
| Java, Kotlin | `.cs/build/jvm/<lang>/src/main/<lang>/ref/<snake_slug>/<approach_snake>/<Solution or ClassName>.<ext>` | Reference files declare no `package`; the materializer prepends `package ref.<snake_slug>.<approach_snake>` (with `;` for Java). Built with `jvm/gradlew -p .cs/build/jvm`, which includes `.cs/runtime/runners/jvm` |
| Go | `.cs/build/go/ref/<snake_slug>/<approach_snake>/<approach_snake>.go` (see the Go file names note below) | None: reference files declare `package <snake_slug>` like the stub, so a file moves between `solutions/` and the practice directory unchanged. Each approach is its own package (import path `csbuild/ref/<snake_slug>/<approach_snake>`), linked into the problem's binary next to the user's package with a generated registration file beside it |
| Project (Python, TypeScript, Go, Java, Kotlin) | `.cs/build/projects/<slug>/<approach>/`: a copy of `starter/`, then of the overlay `solutions/<approach>/`, then the generated test file of every level; rebuilt when the problem's files change | None; run as a [project job](#project-jobs) in that root, which a Java or Kotlin copy builds with its own Gradle files, finding the workspace by walking up |
| Rust | `.cs/build/rust/ref/<snake_slug>/<approach_snake>.rs` | None: reference files are written like the stub (`pub fn`, or `pub struct` with `impl`) and copied unchanged. Each enters the problem's harness crate as the `#[path]` module `ref_<approach_snake>`, so compiler errors name the copy |

### Go file names

The go tool ignores a file whose name ends in `_<GOOS>`, `_<GOARCH>` or `_test` (before `.go`), which would leave the package without its function (`SymbolNotFound`). `layout.go_file_name` therefore appends `_code` to any such stem, for the practice file (`go/practice/sort_test/sort_test_code.go`) and for materialized references and broken references (`sort_windows/sort_windows_code.go`). Package names, directories and the `solutions/<approach>.go` files keep their plain names; only the name of the file the toolchain reads changes.

For JVM bench the classpath joins the user's `practice.*` classes and the `ref.*` classes; package names never collide.

## Conformance suite

`runners/conformance/` holds fixture problems in the normal problem format whose reference approaches are identity functions (return the argument unchanged) for every DSL type, plus fixtures for error paths: exception, `invalid_output`, missing symbol, hang, user printing to stdout, `ref_of`, `output_from`, `no_alias_with`, cyclic ListNode input, and decimal and date arithmetic (inputs that keep their scale, canonical outputs, rounding modes, days across leap years). `cstudy verify --conformance` runs each fixture in every language its `meta.yaml` lists and also compiles every generated stub; a runner that does not support a feature yet leaves the fixture's languages without it (Go lists 9001 to 9017 and 9019 to 9021, Rust the same except 9006 and 9010, which [S13](authoring.md#static) keeps out of Rust). It is a Phase 0 exit criterion and must pass before any runner change merges.

Project fixtures, each listing its one language: `9022-conformance-project-python` and `9023-conformance-project-typescript`, two-file projects whose entry imports a sibling module by package path and by relative path (grading); `9024-conformance-suite-pytest` and `9025-conformance-suite-node-test`, suites with a test that passes, one that fails an assertion, one that raises, one that hangs, one that prints and one that ends the process (suite statuses, output capture, hang guard and restart). `expectations.json` gains per-test outcomes for suite fixtures. Go adds `9030-conformance-project-go`, a project whose entry's package imports a subpackage of the module (grading through the overlay), and `9031-conformance-suite-go-test`, a suite with a test that passes, one that fails an assertion, a failing subtest, one that panics, one that prints, one that ends the process, one that hangs, and a package whose test file does not compile ([Go project jobs](#go-project-jobs)).

The JVM's project fixtures: `9026-conformance-project-java` and `9027-conformance-project-kotlin`, whose entry uses a class of its own package and one of a subpackage (grading on the main runtime classpath); `9028-conformance-suite-junit-java` and `9029-conformance-suite-junit-kotlin`, suites with the six tests above, a class whose `@BeforeAll` fails (reported once, under the class's id, and left out of every restart after it), a disabled test, a failed assumption and a parameterized test (`[1]`, `[2]`).

Fixtures live in `runners/conformance/<id>-<slug>/`; each language adds its reference files as `solutions/<approach>.<ext>`. `runners/conformance/expectations.json` (schema `schemas/conformance.schema.json`) gives the expected outcome per fixture and approach (`pass`, `error`, `invalid_output`, `timeout`, `load_error`) with per-case overrides, and `runners/conformance/README.md` states what every approach does in each language.
