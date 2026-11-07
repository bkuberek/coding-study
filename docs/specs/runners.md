# Spec: Runners and Stub Generation

A runner is a small program per runtime that loads one target (the user's file, a reference approach, or a [project folder](#project-jobs)), deserializes case inputs, invokes the target, and serializes outputs or measurements. It never sees expected values and never judges results. There are five runners: Python, TypeScript, JVM (shared by Java and Kotlin), Go and Rust ([ADR 0012](../decisions/0012-go-and-rust.md)). Rows and fields below marked planned describe parts that nothing implements yet.

## Decisions

| Decision | Choice | Rejected alternative |
|----------|--------|----------------------|
| Who compares | CLI core (Python, once) | Comparators in each runner: 3 implementations of float, multiset and checker logic |
| Result channel | JSON Lines written to a file passed as `--out` | stdout: user `print` calls would corrupt the protocol |
| User output | Captured per case inside the runner, truncated to 4 KiB with a fixed notice, returned in the event | Interleaved terminal output with no case attribution |
| Hang protection | CLI-side inactivity watchdog kills the process group | In-runner timeouts: Python and JVM cannot safely kill a running thread |
| A `cstudy` that dies | An orphan guard process per launch kills the process group once `cstudy`'s end of a pipe closes ([Process lifecycle](#process-lifecycle)) | A watchdog thread in each runner (end of standard input, or polling `getppid`): five implementations, which a debugger that suspends every thread, or a C call that holds Python's GIL, keeps from acting, and which cannot reach what `cstudy` starts itself (a Rust test, Delve, `debugserver`). `PR_SET_PDEATHSIG`: Linux only, fires when the starting thread exits, and reaches the direct child only |
| Batching | One process runs many jobs (verify, bench) | One process per problem: JVM start cost x 200 |
| Concurrent stress | The CLI expands scenarios and judges invariants; runners execute literal per-worker scripts and record results ([Concurrent jobs](#concurrent-jobs)) | Scenario templates and invariants in each runner |
| Time in a project | A virtual clock that each language's own test facility provides, driven by the runner and the generated tests alike ([Virtual clock and stress in project jobs](#virtual-clock-and-stress-in-project-jobs)) | The real clock with tolerances: a 30 s timeout takes 30 s, and a busy machine fires timers late |

## Invocation

| Runner | Prepare (before each run) | Command | cwd |
|--------|---------------------------|---------|-----|
| Python | none (`cstudy doctor --fix` runs `uv sync` once) | `python/.venv/bin/python -m cs_runner --request R --out O` | `python` |
| TypeScript | none | `node .cs/runtime/runners/typescript/runner.ts --request R --out O` | `typescript` |
| Java | `./gradlew -q --console=plain --no-watch-fs :java:csClasspath -Pcs.only=<snake_slug>` | `java -cp <classpath> cs.runner.Main --request R --out O` | `jvm` |
| Kotlin | `./gradlew -q --console=plain --no-watch-fs :kotlin:csClasspath -Pcs.only=<snake_slug>` | same as Java | `jvm` |
| Go | `go build -json [-overlay gen/<snake_slug>/overlay.json] -o bin/<scope>/<snake_slug> ./cmd/<scope>/<snake_slug>` in `.cs/build/go` ([Go build details](#go-build-details)) | `.cs/build/go/run/<pid>-<random>/<snake_slug> --request R --out O`, a private copy of the binary | `.cs/build/go` |
| Rust | `cargo build --offline --release --message-format=json --target <host> -p <scope>_<snake_slug>` in `.cs/build/rust`, with one shared `CARGO_TARGET_DIR` ([Rust build details](#rust-build-details)) | `.cs/build/rust/run/<pid>-<random>/<scope>_<snake_slug> --request R --out O`, a private copy of the binary | `.cs/build/rust` |

Paths are relative to the workspace root, and the `java` of the JVM rows is the selected JDK's `bin/java` ([the JDK and the release level](#the-jdk-and-the-release-level)). The runners themselves run from the workspace's [runner runtime](installation-and-workspaces.md#runner-runtime) in `.cs/runtime/runners/`, a copy of the content's `runners/` that `cstudy` refreshes before the first runner of a command when the content changed. `R` and `O` live in `.cs/runs/<run_id>/` as `request-<n>.json` and `events-<n>.jsonl`, one pair per restart `n`; the last 20 runs are kept. The process starts in its own process group, which ends with the run, or with `cstudy` if it dies first ([Process lifecycle](#process-lifecycle)).

A [project job](#project-jobs) starts in the project root instead: the Python runner adds `-P` and its own environment there, Go launches binaries of its own ([Go project jobs](#go-project-jobs)), Java and Kotlin build the project folder with its own Gradle build ([JVM project builds](#jvm-project-builds)), and a Rust project builds in `.cs/build/rust-projects/<slug>` with the dev profile ([Rust projects](#rust-projects)).

### JVM build details

| Item | Rule |
|------|------|
| `-Pcs.only=<snake_slug>` | Restricts the main source set to `practice/<snake_slug>/**`, so a broken file for another problem never blocks this one. IntelliJ builds without the property and sees everything. |
| `csClasspath` task | Depends on `classes`; writes the runtime classpath (classes dir plus runner and support jars) to `build/cs/runtime-classpath.txt` |
| Gradle settings | Daemon on, configuration cache on, `org.gradle.console=plain`. Every build `cstudy` runs passes `--no-watch-fs`, so Gradle reads the sources from disk: on macOS, watch events for files written just before a build can arrive late, and Gradle then reports the compile task up to date over the changed sources |
| JVM flags | `-XX:+UseSerialGC -Xshare:auto`; no tiering flags (they distort performance cases) |
| Compile errors | Gradle exit code non-zero: the CLI prints compiler lines mentioning the user's file (max 40 lines) and exits 2. Gradle prints them twice, the second time indented under its failure report: the first copy is kept (the second only when it is the only one). Each error is a [diagnostic](cli.md#diagnostics) at the line and column the compiler names, from the absolute path or `file://` URL it prints |
| Cold start | If no daemon is running, the CLI prints `warming Gradle daemon (first run)` before building |
| Locking | `-Pcs.only` narrows each build to one problem, so every build rewrites the shared output directories and deletes the classes of the problem built before. Per Gradle project and language, one `cstudy` process at a time writes the reference sources (and removes the other approaches' files), runs Gradle and copies the built class directories: an exclusive `flock` on `.cs/build/jvm-locks/<references or practice>-<lang>.lock`. A process that finds the lock taken prints `waiting for another cstudy build in this workspace` and waits; the kernel drops the lock when its holder ends, however it ends. Java and Kotlin use different locks and still build side by side. |
| Runtime jars | Both Gradle projects include the runtime's `runners/jvm` build, so any build after a change to the runner's sources rebuilds `runner.jar` and `support.jar`, and Gradle writes a jar in place: two builds doing so at once, or a JVM reading a jar while it is rewritten, failed before `hello` (`NoClassDefFoundError`). Every build also holds `.cs/build/jvm-locks/runtime.lock`: shared while the runtime's sources and jars (path, size and modification time) are as the last build under the exclusive lock left them, recorded in `runtime-jars.txt`, and exclusive otherwise. So the first builds after a change take turns, and later ones still run side by side. The [runtime refresh](installation-and-workspaces.md#runner-runtime) holds it exclusively while it changes `runners/jvm`, so no build reads the sources half copied. |
| Per-run class copy | Under the locks, the build's class directories (the classpath entries below the subproject's `build/`) and the runtime's runner and support jars are copied into `.cs/build/jvm-runs/<pid>-<random>/`, and the JVM's `-cp` names the copies; the jars in Gradle's cache keep their paths. A later build, for another problem or after a change to the runner, cannot take classes away from a JVM that loads them lazily. The runner process removes the copy when the run ends (completed, failed or interrupted); the next preparation removes copies whose process no longer exists (killed). |

The lock and the copy protect against other `cstudy` processes. A Gradle build started by anything else on the same project (a script, an IDE build of `.cs/build/jvm`) does not take the lock and can still delete classes between the build and the copy.

### The JDK and the release level

Every JVM build and run uses the JDK that [the shell selects](cli.md#the-selected-jdk), 21 to 26 ([ADR 0016](../decisions/0016-jdk-range.md)). The version of a build never comes from a toolchain, and one release level serves each build.

| Item | Rule |
|------|------|
| Selected JDK | `cstudy` sets `JAVA_HOME` in the wrapper's environment to the selected JDK's home and passes `-Dorg.gradle.java.home=<home>`, which outranks a setting in the Gradle user home, so Gradle's daemon, javac and kotlinc all run on it. The runner process is `<home>/bin/java`, with the flags of [JVM build details](#jvm-build-details), not the first `java` on `PATH` |
| No toolchain | No plugin and no runner module sets a Gradle toolchain, and no toolchain resolver is configured, so nothing downloads a JDK (NFR-6). Compiling uses the JDK that the daemon runs on |
| Release level | Every Java compile gets `options.release`, and every Kotlin compile `jvmTarget` and `-Xjdk-release`, at one level per build: the Gradle property `cs.release` when `cstudy` passes one, else the feature release of the build's JDK, capped at the top of the supported range (26). The `cs.practice` and `cs.project` plugins set it, so the workspace's `jvm/java` and `jvm/kotlin` projects, the project folders and an IDE's Gradle import derive the same level from the same JDK. Kotlin needs it set explicitly: without it a build on JDK 27 fails on inconsistent targets between `compileJava` and `compileKotlin` |
| Your code | Compiles at your JDK's level, so JDK 26 compiles a problem that needs only 21 with everything JDK 26 offers. One level serves every problem of `jvm/java` and `jvm/kotlin`, since an IDE imports their one source set |
| Content | What `cstudy verify` and `cstudy bench` build from the content (references, broken references, buggy files, generated stubs, and project starters with their reference overlays) compiles with `-Pcs.release=<the problem's minimum>` (21 without a `jdk.min`), so `cstudy verify` on any JDK of the range rejects an API or a language feature newer than the declared minimum, with no second JDK installed. These builds, under `.cs/build/`, are `cstudy`'s own and no IDE imports them |
| Runner classes | The runner, support, suite and plugin modules compile at release 21, the supported minimum, so they load on every JDK that the range or an opt-in reaches. They are built on the selected JDK like everything else |
| Configuration cache | The plugins read the level from the build's JVM. After a JDK switch the cached configuration is not reused (Gradle reports that the JVM changed) and a new entry is stored, and the level follows the JDK |
| Daemons | Gradle keeps one daemon per JDK: switching JDKs starts another daemon and recompiles once |
| Above the range | A problem that declares a `max` which reaches the selected JDK builds at release 26 and runs on that JDK |
| Plugin module | The plugins compile against the Kotlin Gradle plugin's API only, compile-only and at the workspace's Kotlin version, which the runners' build resolves from the plugin repository after Maven Central. A workspace whose `cstudy doctor --fix` already built Kotlin has it cached and upgrades offline; a new workspace caches it in its first, online, `cstudy doctor --fix` (NFR-6) |
| Upgrade | No migration step: the [runtime refresh](installation-and-workspaces.md#runner-runtime) brings the new plugins, and the `jvm/` template files name no JDK. The first build after the upgrade, and after any JDK switch, recompiles |
| Preview features | `cstudy` never passes `--enable-preview` |

### Go build details

| Item | Rule |
|------|------|
| Toolchain | Go 1.25 or newer: Go 1.24 introduced `go build -json`, and `testing/synctest.Test`, which grades a [virtual-clock project](#virtual-clock-and-stress-in-project-jobs), is Go 1.25 API ([ADR 0017](../decisions/0017-async-project-problems.md)). Environment `GOENV=off`, `GOTOOLCHAIN=local`, `GOPROXY=off`, `GOFLAGS=-mod=readonly`, `GO111MODULE=on`, `CGO_ENABLED=0` and `GOWORK=.cs/build/go/go.work`, with the user's `GOOS`, `GOARCH`, `GOEXPERIMENT`, `GOFIPS140`, the instruction-set levels (`GOAMD64`, `GOARM`, `GOARM64`, `GO386`, `GOMIPS`, `GOMIPS64`, `GOPPC64`, `GORISCV64`), `CC`, `CXX` and every `CGO_*` removed, so a build never downloads a toolchain or a module, never runs a C compiler, and builds for this machine whatever the user's `go env -w` file or environment says (an empty `GOFLAGS` would not do: the go command reads it as unset and falls back to that file); `PATH`, the proxy variables, `GOCACHE` and the rest stay, and the user's build cache is kept, so the standard library and the runner compile once per machine |
| Build module | `.cs/build/go` is module `csbuild`, which requires `cstudy` and the vendored modules; its `go.work` uses it and the workspace's `go/` (module `workspace`), replaces the runner module `cstudy` with `.cs/runtime/runners/go` and each vendored module with its copy there. The build module and its `go.work` say `go 1.25`, the line of the runner module, since a `go.work` must name at least the `go` line of every module it uses; the workspace's `go/go.mod`, which says `go 1.24`, builds under it |
| Vendored modules | `github.com/shopspring/decimal` v1.5.0, the Go type of `decimal`, is copied into `runners/go/third_party/github.com/shopspring/decimal` (its `go.mod`, `LICENSE`, `README.md` and non-test sources; `runners/go/third_party/README.md` records the source and hash). `runners/go/go.mod`, the workspace's `go/go.mod` and the build's `go.work` reach it through `replace`, so no build or editor needs the network or a module cache. A `go/go.mod` written before the module was vendored still builds, since the build's `go.work` supplies the `replace`, but the editor cannot resolve the import until its `require` and `replace` lines are added |
| Binary | One per problem and scope (`test`, `verify`, `bench`): `cmd/<scope>/<snake_slug>/main.go` imports the user's package `workspace/practice/<snake_slug>` and each reference package `csbuild/ref/<snake_slug>/<approach_snake>`, and passes their registrations, and the thunks of class kinds, to `runner.Main` keyed by target id (`user`, `ref/<approach>`) |
| Registration | Each package gets `zz_cs_targets.go`: `var CsTargets = map[string]any{"twoSum": twoSum}`, or the constructor (`NewLRUCache`) for class kinds, under the package clause read from its file. The user's enters through `go build -overlay` (the replacement file is `gen/<snake_slug>/user_targets.go`), so nothing is written to `go/practice` and compiler errors and breakpoints name the real file; a reference's is written next to its copy |
| Method thunks | A design or progressive package also gets `zz_cs_thunks.go` (the user's replacement file is `gen/<snake_slug>/zz_cs_thunks.go`), apart from the registration so that it can be left out alone. `var CsThunks` holds a nil `*Class` as `Receiver` and, for each declared method, a function that asserts the receiver and each argument to the Go type of the [mapping](problem-format.md#go-and-rust-mapping) and returns the result as an `any`: `"Insert": func(r any, a []any) any { return r.(*RandomizedSet).Insert(a[0].(int)) }`, with `return nil` after a method that returns nothing. Node types are spelled `*support.ListNode`, so the file does not depend on the stub's aliases, and it imports only what its parameter types use. A function problem gets none (it is called once per input), and neither does a concurrent class (stress workers keep reflection and it has no bench) |
| Method dispatch | The runner still checks every signature by reflection when a job loads, so the result of a mismatch does not depend on the thunks. It calls a method through its thunk when the type the constructor returns is the thunks' `Receiver`, and through `reflect.Value.Call` otherwise, so a class that returns another type or has no thunk keeps working. In a bench the arguments of every operation are decoded to `[]any` before the clock starts, as they are decoded for reflection, and the test path uses the same thunks, so a case produces its results the same way in both. A traceback leaves out the frames of `zz_cs_thunks.go`. The point is the timed region: a reflective call costs about 120 to 250 ns and four allocations per operation, a constant per call that hides a cheap quadratic scan from the [ladder check](performance-analysis.md#ladder-check) (a linear list scan over at most 10^5 values measured about n^1.4, and its time / n^2 varied 5 to 8 times against the 4x tolerance); a thunk call costs about 10 to 20 ns |
| Compile errors | Diagnostics in the user's or a reference file: exit 2 with the compiler lines, paths relative to the workspace (at most 40); in a bench, a reference's are a content error. Diagnostics only in registration files: the build runs again without those registrations (a second compile in that case only), and the runner reports `load_error` `SymbolNotFound` with the compiler's message, such as `the package defines no function "twoSum": undefined: twoSum`. Diagnostics in a thunk file mean a method whose parameters differ from the signature, or a class type that is missing: the same second build leaves that file's thunks out (the file stays, empty), and the runner reports `SignatureMismatch` or `SymbolNotFound` from its own check. A failure with no diagnostics, or with diagnostics in the runner or the main package, is an environment error (exit 4) with the output tail |
| Concurrent `cstudy` processes | Generation and build hold an exclusive `flock` on `.cs/build/go/.cstudy.lock`, which the [runtime refresh](installation-and-workspaces.md#runner-runtime) also holds while it changes `runners/go`, so no build reads the sources half copied. The launched file is `run/<pid>-<random>/<snake_slug>`, a copy of the built binary that no other build overwrites; `RunnerProcess` removes its directory when the run ends (completed, failed or interrupted), and the next build removes the directories of processes that no longer exist (killed) |
| Writes | Generated files are rewritten only when their content changes |
| Cold start | Before the first build of a workspace the CLI prints `compiling the Go runner and standard library (first run)`; the build note is `go, cold`, then `go, warm` |
| Debug build | `cstudy test --debug` adds `-gcflags=all=-N -l` (no optimizations, no inlining, so every line and variable of the user's code can be inspected) and writes `bin/debug/<snake_slug>`, apart from the optimized binaries. The first debug build compiles the standard library again; before it the CLI prints `compiling the Go runner and standard library for debugging (first debug run)` ([debug mode](#debug-mode)) |

### Rust build details

| Item | Rule |
|------|------|
| Toolchain | Rust 1.80 or newer through rustup (`cargo` and `rustc` on PATH). The runner crates, the generated harness packages and the practice project declare `rust-version = "1.80"`, so clippy flags APIs newer than that (`incompatible_msrv`). The runner crates' only dependencies are vendored, so builds run with `--offline`, and without `--locked`, which fails whenever a harness package joins the workspace. The host target triple comes from `rustc -vV` once and is kept in `.cs/build/rust/host-target` |
| Build workspace | `.cs/build/rust` is a Cargo workspace with one harness package per problem and scope (`test/<snake_slug>`, `verify/<snake_slug>`, `bench/<snake_slug>`, package `<scope>_<snake_slug>`), listed one by one because Cargo reads a glob that matches nothing as a path. Each package depends on `cs_runner` and `cs_support` in `.cs/runtime/runners/rust` by relative path, and on `rust_decimal` and `chrono` as `cs_runner` declares them, so a solution's `use rust_decimal::Decimal;` resolves; `CARGO_TARGET_DIR=.cs/build/rust/target` is shared, so the runner crates compile once per workspace |
| Vendored crates | `rust_decimal` 1.43.0 (feature `maths`) and `chrono` 0.4.45 (feature `std`), the types of `decimal` and `date`, without default features, and their dependencies `arrayvec`, `num-traits` and `autocfg`, are copied into `runners/rust/vendor` by `cargo vendor`, without their tests, benches and examples (`runners/rust/vendor/README.md`). So is tokio 1.53.3 with `macros`, `rt`, `sync`, `test-util` and `time`, the runtime and paused clock of [virtual-clock projects](#virtual-clock-and-stress-in-project-jobs), with `tokio-macros`, `pin-project-lite`, `proc-macro2`, `quote`, `syn` and `unicode-ident`: 1.53 is the newest release whose MSRV (1.71) is within Rust 1.80. `cs_runner` declares it behind its `clock` feature, which only a clock project's harness turns on, so no other build compiles it. The vendored sources come to 8.8 MB, 2.3 MB without tokio. Every build passes `--config source.crates-io.replace-with="cstudy-vendor"` and `--config source.cstudy-vendor.directory="<runtime>/rust/vendor"`, which outrank a user's `config.toml`, so crates.io is never contacted and a fresh `CARGO_HOME` builds as well as a warm one. `rust_decimal`'s `std` feature is left out: it adds only an `Error` impl, but its weak `dep?/std` features would lock, and so vendor, 48 optional crates |
| Bridge | Each package's `main.rs` is generated from the signature. The user's file and each reference copy enter as `#[path = "<absolute file>"] mod user;` and `mod ref_<approach_snake>;`, so compiler errors, panics and breakpoints name the real file. Per target, the bridge decodes every argument with its declared Rust type, calls the function (`user::two_sum(arg_nums, arg_target)`), or for a class kind `LRUCache::new` and a `match` on the operation's canonical name, and boxes the result for encoding. A name that is a Rust keyword is a raw identifier in the stub and the bridge (`instance.r#move(arg_source, arg_target)`), while the operation stays `move`. A concurrent class is registered as `Entry::Concurrent`: its constructor hands the instance to `cs_runner::shared`, which requires `Send + Sync` (a `RefCell` or `Rc` field is a `load_error` `SignatureMismatch` such as `` `RefCell<VecDeque<i32>>` cannot be shared between threads safely ``), and every decoded call is `Send`, so a concurrent problem with node types cannot run in Rust (`load_error` `UnsupportedType`). Modifiers are generated too: a `ref_of` argument is looked up after the argument it points into, and `as: index` and `no_alias_with` take the parameter's node addresses before the call, which runs with freed memory retained so no new node can reuse an old node's address ([Node modifiers](#node-modifiers)) |
| Replaced sources | Cargo rebuilds a crate when a source is newer than the last build, so a file replaced by a copy that keeps an older time (`rsync -a`, `cp -p`) would run the code of the build before. Each build, under its lock and before Cargo runs, records the SHA-256 of the practice file (`.cs/build/rust/.sources/<snake_slug>.json`; for a project, of every `*.rs` file and `Cargo.toml` and `Cargo.lock` in the folder, outside `target` and hidden folders, in `.cs/build/rust-projects/<slug>/sources.json`) and touches every file whose digest differs from the record, or that the record lacks. The first build has no record and touches nothing. A file that cannot be read or touched is left as it is |
| Release profile | `opt-level = 3`, `overflow-checks = true`, `debug = "line-tables-only"`, `panic = "unwind"`, `strip = "none"` and the platform's default `split-debuginfo` (`"unpacked"` on macOS, `"off"` on Linux), in the workspace manifest and again as `--config profile.release.*`, which outranks a user's `config.toml`: `--perf` numbers are real, an `i32` overflow panics instead of wrapping, traces have line numbers and function names, and a panic is caught per case |
| The user's Cargo setup | Cannot break or redirect a build: `CARGO_ENCODED_RUSTFLAGS` is set empty (it outranks `RUSTFLAGS` and every `rustflags` setting), `RUSTC_WRAPPER` and `RUSTC_WORKSPACE_WRAPPER` are set empty (which turns off a configured wrapper such as sccache), `--target <host>` overrides a configured `build.target`, `--config build.rustc="rustc"` and `--config target.<host>.linker="cc"` pin the compiler and the host's linker to the platform's defaults, which outranks a `build.rustc` or `target.<host>.linker` of the environment or of any `config.toml` (a linker or compiler that is missing on this machine, or built for another target, no longer fails the build), and the user's `RUSTFLAGS`, `RUSTC`, `RUSTC_BOOTSTRAP`, `RUSTDOC`, `RUSTDOCFLAGS`, `CARGO_ENCODED_RUSTDOCFLAGS`, `CARGO_INCREMENTAL` and `CARGO_BUILD_*`, `CARGO_PROFILE_*`, `CARGO_TARGET_*` (the target directory, and each triple's linker, runner and flags), `CARGO_TERM_*` and `CARGO_UNSTABLE_*` variables are removed; `PATH`, the proxy variables, `CARGO_HOME` and the rustup variables stay |
| Compile errors | Classified by the primary span of each error-level compiler message only: a call whose signature does not match also gets a child note "function defined here" in the user's file. Errors in the user's or a reference file: exit 2 with `path:line:column: error[<code>]: <message>`, the span's label and up to two `help` or `note` lines (one that suggests a replacement first), paths relative to the workspace (at most 40 lines); in a bench, a reference's are a content error. Errors only in the bridge: the build runs again with those targets marked unavailable, keeping their `mod` so a hidden error in their file still fails the build, and the runner reports `load_error` with the compiler's message in the user's terms, where a keyword name is the signature's (`move`, not `r#move`). `SymbolNotFound` keeps only the compiler's suggestions when it has any: ``cannot find function `two_sum` in `two_sum.rs`; a function with a similar name exists: `twosum` ``, ``no method named `get` found for mutable reference `&mut LRUCache` in the current scope; there is a method `gett` with a similar name``, ``function `two_sum` is private; declare it pub``. `SignatureMismatch`: ``mismatched types: parameter `nums` is `&[i32]`, the signature declares `Vec<i32>` ``, ``mismatched types: the result is `Vec<usize>`, the signature declares `Vec<i32>` ``. A failure with no compiler error, or errors in the runner crates, is an environment error (exit 4) with the output tail |
| Concurrent `cstudy` processes, writes, cold start | As in Go: generation and build hold an exclusive `flock` on `.cs/build/rust/.cstudy.lock`, and a shared one on `.cs/build/rust/runtime.lock` (the [runtime refresh](installation-and-workspaces.md#runner-runtime) holds it exclusively while it changes `runners/rust`, so no build reads the crates half copied); every run launches its own copy of the binary (`run/<pid>-<random>/<scope>_<snake_slug>`, removed when the run ends, as in Go), and generated files are rewritten only when their content changes (Cargo fingerprints sources by modification time, so rewriting identical bytes would rebuild). Before the first build of a workspace the CLI prints `compiling the Rust runner (first run)`; the build note is `rust, cold`, then `rust, warm` |
| Debug build | `cstudy test --debug` builds with `--profile dev` instead of `--release`: `opt-level = 0`, `debug = true`, and the release profile's `overflow-checks`, `panic`, `strip` and `split-debuginfo`, pinned the same way (workspace manifest and `--config profile.dev.*`), so a debugger sees every line and variable. The first debug build compiles the runner crates again; before it the CLI prints `compiling the Rust runner for debugging (first debug run)` ([debug mode](#debug-mode)) |
| Editor project | `rust/Cargo.toml` lists each started problem as an `[[example]]` with `crate-type = ["lib"]` ([layout](installation-and-workspaces.md#layout)) and has `rust_decimal` and `chrono` as dev-dependencies; `rust/.cargo/config.toml` points crates.io at the runtime's vendored crates, for the `cargo` commands rust-analyzer runs in `rust/`. The build reads neither |
| Never | `ref_of` or `as: index` on a `ListNode` (`load_error` `UnsupportedType`) and cyclic list inputs (`InvalidInput`): an `Option<Box<ListNode>>` has one owner per node. [S13](authoring.md#static) keeps `rust` out of such problems |

### Build timeouts

Every build step that `cstudy` runs for a runner has a time limit, so a toolchain that never finishes (a package-cache lock held by a process that is gone, a stuck procedural macro, a network attempt that is never answered) cannot hang the command.

| Item | Rule |
|------|------|
| Steps | `go build` (single files and projects, including the suite runner), `cargo build`, `rustc -vV` (the host and release probes), the Gradle wrapper of the JVM builds (`Gradle build`) and `tsc` of `--typecheck` |
| Limit | 300 s for each of them except `tsc`, which keeps its 120 s. It applies to each invocation, so the second pass of a Go or Rust build gets its own, and it is meant to be far above a cold build on a loaded machine |
| Process group | The tool starts in a session of its own and, on expiry or an interrupt, `SIGKILL` goes to its whole process group, so `pnpm`'s `tsc`, `gradlew`'s client and Cargo's `rustc` and build scripts end with it. A Gradle daemon is a session of its own, not part of the group, and stays running as it does after any build |
| Error | An environment error (exit 4) naming the step and the limit, such as `cargo build did not finish within 300 s and was stopped`, with the last (at most five) lines the tool wrote. The workspace build lock is released, and the next build runs the step again |
| Configuration | The limits are constants of the adapters (`DEFAULT_BUILD_TIMEOUT_SECONDS` in `adapters/languages/bounded_process.py`, `TYPECHECK_TIMEOUT_SECONDS` in the TypeScript runner), and each toolchain adapter takes its own as a constructor argument. [Configuration](cli.md#configuration) has no key for them yet |

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

What a runner inherits from your shell is the allowlist of [Process environment](#process-environment).

| Concern | Python | TypeScript | JVM | Go | Rust |
|---------|--------|------------|-----|----|------|
| Deep recursion | cases run in a worker thread created after `threading.stack_size(256 MiB)`; `sys.setrecursionlimit(10**6)` | Node default stack; content keeps depth at or under 3000 | cases run in a `Thread` with 256 MiB stack size | cases run on the main goroutine, whose stack grows on demand up to Go's 1 GB limit | cases run on a thread named `cs-runner-cases` with a 256 MiB stack; a stack overflow aborts the process (a crash) |
| Output capture | `contextlib.redirect_stdout` / `redirect_stderr` per case | replace `console.log/info/warn/error` and wrap `process.stdout.write` per case | `System.setOut` / `System.setErr` per case | file descriptors 1 and 2 are redirected to one pipe per case with `dup2`, because the `println` builtin writes to fd 2 directly; `debug.SetCrashOutput` (Go 1.23) still sends a fatal error to the real standard error | file descriptors 1 and 2 are redirected to one pipe per case with `dup2`, and `io::stdout()` is flushed before they are restored, because `print!` is buffered and the standard library's capture is unstable |
| Output limit | Standard output and standard error share one buffer that keeps the first 4096 bytes of UTF-8, never splitting a character; when anything was dropped, the runner appends exactly `\n[output truncated at 4 KiB]\n` | same | same | same | same |
| Fresh inputs | deserialize per case (and per bench repetition) | same | same | same | same |
| Node classes | duck-typed field access, never `instanceof` | same | `cs.support` classes | `cstudy/support` types (`*support.ListNode`, through the stubs' aliases): types must match exactly | `cs_support` types (`Option<Box<ListNode>>`, `Option<Rc<RefCell<TreeNode>>>`, `Option<Rc<RefCell<GraphNode>>>`), checked by the compiler in the bridge |
| Decimal and date output | `decimal` must be a finite `Decimal` and is written as `format(value, "f")` without trailing fractional zeros (`-0` as `0`); `date` must be a `date` that is not a `datetime`, written by `isoformat()`. Anything else, `float` and `int` included, is `invalid_output` | `decimal` must be a `Decimal` from `#support`, recognized by its `unscaled` and `scale` fields, written the same way; `date` must be a `YYYY-MM-DD` string naming a real day | `decimal` must be a `BigDecimal`, written by `stripTrailingZeros().toPlainString()` (`0` for zero); `date` must be a `LocalDate` in years 0001 to 9999. `null` and other classes are `invalid_output` | `decimal` is a `decimal.Decimal`, written from its coefficient and exponent without trailing fractional zeros (`0` for zero), whatever the package settings `TrimTrailingZeros` and `UseScientificNotation` say; `date` must be a `time.Time` in `time.UTC` at midnight, in years 0001 to 9999. Another location, a time of day or a year outside that range is `invalid_output` | `decimal` is a `rust_decimal::Decimal`, written by `normalize()` and `Display` (no trailing fractional zeros, `-0` as `0`, never an exponent); an input that does not fit it, more than 28 digits after the point or a magnitude of 2^96 or more, is `InvalidInput`. `date` is a `chrono::NaiveDate`; a year outside 0001 to 9999 is `invalid_output`. The compiler checks both types in the bridge |
| Decimal context | every case starts with a fresh `decimal.Context()` (precision 28, `ROUND_HALF_EVEN`), so a solution that changes the context cannot affect a later case | none | none | every case starts with shopspring/decimal's default package settings (`DivisionPrecision` 16 and the rest), so a solution that changes one cannot affect a later case or another target | none |
| Exit from user code | `SystemExit` caught as case error | `process.exit` is replaced with a throwing stub | `System.exit` cannot be blocked on any supported JDK (the security manager that could is off on JDK 21 to 23 and gone from JDK 24); the CLI reports the runner exit as a crash on the current case | `os.Exit` cannot be blocked: reported as a crash, as on the JVM | `std::process::exit` cannot be blocked: reported as a crash |

## Process environment

Every process that runs user code, or a tool on it, begins with an allowlisted part of the environment of `cstudy` and adds its own variables, so a token, a key or a password in your shell does not reach your code, its tests or the tools beside them ([ADR 0019](../decisions/0019-service-projects.md#phases), P2, built for every problem and every language). The policy is `allowed_environment` in `domain/process_environment.py`; the adapters hand it `os.environ` through `inherited_environment` in `adapters/process_environment.py`, and none passes `os.environ` on.

| Concern | Rule |
|---------|------|
| Who gets it | The runner of every language, in a test, a bench, a debug run, a project job and a suite; the builds (Gradle, `go build` and `go test -c`, `cargo build` and `rustc`, the TypeScript type-check); a Rust test binary and its debug server; the setup commands and version probes of `cstudy doctor` (`uv sync`, `pnpm install`, Gradle, the installs of the language servers), which run code of the project and of its packages; and a [language server](web-ui.md#code-intelligence-sessions). One list for all of them, since a build that downloads a package needs the same network settings as the run |
| Who does not | A child `cstudy` that `cstudy serve` starts, which needs its own configuration and applies this rule to what it runs; the editor `cstudy config edit` opens; `git`; the probes that run no project code (`ps`, `pmset`, `xcode-select`, the JDK's own `java` probe) |
| What is added | The launch's own variables, set after the filter and winning over it: `JAVA_HOME` and `-Dorg.gradle.java.home` for Gradle, `UV_NO_SYNC` and `PYTHONPYCACHEPREFIX` for Python, the pinned Go and Cargo settings, `NODE_OPTIONS` with the `hide_paths.cjs` preload for a Node language server |
| Exact names | `PATH`, `HOME`, `USER`, `LOGNAME`, `SHELL`; `LANG`, `LANGUAGE`, `TZ`; `TERM`, `COLORTERM`, `NO_COLOR`, `FORCE_COLOR`, `CLICOLOR`, `CLICOLOR_FORCE`, `COLUMNS`, `LINES`, `TERMINFO`, `TERMINFO_DIRS`; `TMPDIR`, `TMP`, `TEMP`; `DEVELOPER_DIR` (where `xcrun` finds the linker Rust uses) |
| Python | `VIRTUAL_ENV`, `PYTHONIOENCODING`, `PYTHONUTF8`; of uv's, `UV_CACHE_DIR`, `UV_PYTHON`, `UV_PYTHON_INSTALL_DIR`, `UV_PYTHON_PREFERENCE`, `UV_PYTHON_DOWNLOADS`, `UV_PROJECT_ENVIRONMENT`, `UV_LINK_MODE`, `UV_OFFLINE`, `UV_NO_SYNC`, `UV_NATIVE_TLS`, `UV_SYSTEM_CERTS`, `UV_HTTP_TIMEOUT`. Not `UV_*`, which would pass `UV_PUBLISH_TOKEN`, `UV_GITHUB_TOKEN` and the passwords of `UV_INDEX_*` |
| TypeScript | `NODE_OPTIONS`, `NODE_PATH`, `NODE_NO_WARNINGS`, `NODE_DISABLE_COLORS`, `NODE_COMPILE_CACHE`; `PNPM_HOME`, `COREPACK_HOME`, `COREPACK_ENABLE_AUTO_PIN`, `COREPACK_ENABLE_STRICT`, `COREPACK_ENABLE_DOWNLOAD_PROMPT`; of npm's, `npm_config_` and `NPM_CONFIG_` followed by `cache`, `store_dir`, `cafile`, `proxy`, `https_proxy`, `noproxy` and `strict_ssl`. Not `NODE_*`, which would pass `NODE_AUTH_TOKEN` |
| JVM | `JAVA_HOME`, `JAVA_TOOL_OPTIONS`, `JDK_JAVA_OPTIONS`, `_JAVA_OPTIONS`, `JAVA_OPTS`, `GRADLE_OPTS`, `GRADLE_USER_HOME`, and the prefix `SDKMAN_` |
| Go and Rust | `GOPATH`, `GOCACHE`, `GOMODCACHE`, `GOROOT`, `GOTOOLCHAIN`, `GOTMPDIR`; `CARGO_HOME`, `RUSTUP_HOME`, `RUSTUP_TOOLCHAIN`. The pinned Go and Cargo settings of [Go build details](#go-build-details) and [Rust build details](#rust-build-details) still apply on top |
| Network | `HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY`, `ALL_PROXY`, `FTP_PROXY` and the same in lower case; `SSL_CERT_FILE`, `SSL_CERT_DIR`, `REQUESTS_CA_BUNDLE`, `CURL_CA_BUNDLE`, `NODE_EXTRA_CA_CERTS`, `CARGO_HTTP_CAINFO`, so an install behind a proxy or a network that inspects TLS keeps working. A proxy URL passes as it is, so a credential written into one passes with it |
| Prefixes | `LC_` (locale categories) and `XDG_` (base directories), and `SDKMAN_`. A prefix never passes a name that has `TOKEN`, `SECRET`, `PASSWORD`, `PASSWD`, `CREDENTIAL`, `PRIVATE`, `AUTH` or `KEY` in it, and no exact name has one |
| Everything else | Dropped: `*_TOKEN`, `*_KEY`, `*_SECRET`, `*_PASSWORD`, `AWS_*`, `GITHUB_TOKEN`, `SSH_AUTH_SOCK`, `KUBECONFIG`, `DATABASE_URL`, registry and index URLs and their credentials, and the variables that steer a build or a run: `PYTHONPATH`, `NODE_ENV`, `CI`, `EDITOR`, `LD_PRELOAD`, `GOFLAGS`, `GOOS`, `RUSTFLAGS`, `RUST_BACKTRACE`. A version manager's selection variables (`PYENV_VERSION`, `ASDF_*`, `MISE_*`) are dropped too: the tools they select are found through `PATH` |
| What it is not | A sandbox. User code runs as you and can read what you can, such as `~/.aws/credentials`, and use the network. It stops the inheritance of variables, not access |
| Adding names | There is no setting to pass on another variable. A variable you set in your shell for your own `go` or `pytest` commands does not reach the ones `cstudy` runs; [ADR 0019](../decisions/0019-service-projects.md#decided-by-the-owner) R32 proposed a config key for this, which is not built until a need for one appears |

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
| `stalled` | Concurrent stress runs: workers still unfinished at the run deadline ([Concurrent jobs](#events)). A virtual-clock case: an operation that waits while no task can run and no timer is due, with `op_index`, `reason` and `partial_output` ([Virtual clock](#virtual-clock-and-stress-in-project-jobs)) |
| `failed`, `skipped` | Suite jobs only: an assertion failed, or the framework skipped the test ([Suite job](#suite-job)) |

Every `case_result` carries `duration_ns`; `stdout` and `error.trace` may be omitted when empty.

`load_error` replaces all `case_*` events of a job: `{"event": "load_error", "job_id": ..., "error": {...}}`.

`duration_ns` measures only the call (and serialization is excluded), using `time.perf_counter_ns`, `process.hrtime.bigint()`, `System.nanoTime()` or `std::time::Instant`. Rust panics carry a message and no type, so their `error.type` is `panic`; the trace keeps the frames in the target's file, and in a release build the panic's own location stands in for a function inlined without one.

## Runner exit codes

| Code | Meaning | CLI handling |
|------|---------|--------------|
| 0 | Protocol completed (`bye` written), regardless of case outcomes | Read events |
| 2 | Bad request (unknown protocol version, invalid JSON), while no case is in progress | Internal error, CLI exits 70 |
| 3 | Restart requested after a stress run left threads alive, or a `stalled` virtual-clock case left goroutines or threads behind (only after a `restart_requested` event) | Restart for the remaining cases without using up the crash-restart budget ([Concurrent jobs](#exit-codes-hang-guard-and-restarts-additions)) |
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

## Process lifecycle

Every process `cstudy` starts to run code (a runner, a debug agent or server that holds one, and each test process of a [Rust suite](#rust-projects)) leads a process group of its own, and what it starts stays in that group unless it leaves it: `go test` and its test binaries in the Go runner's, Delve in the Go suite runner's. Runners start no process group of their own and need no code for any of this.

| When | What ends, and how |
|------|--------------------|
| The runner wrote `bye` | `cstudy` waits up to 5 s for it to exit, and kills its process group (SIGKILL) if it has not |
| A hang guard expired, or the runner crashed | Its process group is killed, and the runner restarted ([Hang guard and restarts](#hang-guard-and-restarts)) |
| A debug run ends, however it ends | Its process group, then every process running a file of the launch's private directory ([Debug mode](#debug-mode)) |
| `cstudy` dies without cleaning up (SIGKILL, a crash) | The same, within milliseconds, by the launch's orphan guard |

| Item | Rule |
|------|------|
| Orphan guard | Before each such process starts, `cstudy` starts a guard: its own interpreter running the module `process_liveness.py` as a script (`python -I -S`, standard library only), in a session of its own so that no terminal's signals reach it. Its standard input is a pipe whose writing end only `cstudy` holds (close-on-exec, so no other child inherits it); once the process started, `cstudy` writes its process group id there |
| Trigger | The guard reads the pipe until it ends: the kernel closes the writing end when `cstudy` exits, however it exits, so nothing polls and nothing depends on the runner's state. A runner paused at a breakpoint, a Python runner whose GIL a C call holds, and a TypeScript runner whose event loop a busy case blocks all end the same way. The guard then kills each process group it was given, and in a debug run every process running a file of the launch's private directory, and exits |
| Normal end | After its own cleanup, `cstudy` kills the guard and only then closes the pipe, so a run that ends normally never sets its guard off, and a `cstudy` that dies during that cleanup still leaves nothing behind |
| Window | A `cstudy` killed while it starts a process, before it wrote the group id (about a millisecond), leaves that process running |
| Not covered | A process that leaves its group (`setsid`, `setpgid`, a daemon such as Gradle's, which is meant to outlive a run), unless it runs from a debug run's private directory; and a build (`go build`, `cargo build`, Gradle) that `cstudy` was waiting for, which runs to its end and exits |
| Next start | `cstudy` removes the private directories of compiled runners whose owner process no longer exists ([Go build details](#go-build-details)), and the JVM's class copies ([JVM build details](#jvm-build-details)), but kills nothing: a process still running from such a directory is the guard's to end |

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
| Rust's debug server | macOS: `debugserver` from `LLDB_DEBUGSERVER_PATH`, PATH, or the `LLDB.framework` of the selected developer directory (`DEVELOPER_DIR`, else `xcode-select -p`: an Xcode's `SharedFrameworks`, or the Command Line Tools' `PrivateFrameworks`), as `lldb` itself finds it. Linux: `lldb-server` on PATH, where the `lldb` package of Debian and Ubuntu links it (a versioned package alone, such as `lldb-18`, installs only `lldb-server-18`). Missing, it is an environment error before anything is built: ``cannot debug rust: debugserver was not found; run `xcode-select --install` (<toolchains guide>#rust)``, or ``lldb-server was not found; install your distribution's lldb package``; `cstudy doctor` warns when it is missing. macOS asks for permission to debug unless the user is in the `_developer` group or developer mode is on (`DevToolsSecurity -enable`). `lldb-server` turns off address space randomization for the runner with the `personality` system call, which Docker's default seccomp profile refuses: in a container, the launch fails with `personality set failed: Operation not permitted`, an environment error that shows the server's output, unless the container runs with `--security-opt seccomp=unconfined`. Delve needs no such option |
| Stopping | Ctrl-C, SIGTERM and SIGHUP (what an IDE sends when its task is stopped) kill the runner's process group, so a stopped run never leaves the debug port held. When a debug run ends, however it ends, every process still running a file of the launch's private directory (`scratch`: the copy of the compiled runner, for Go and Rust) is killed too, by executable path and not by group: the first word of `/proc/<pid>/cmdline` on Linux, of `ps -axww -o pid=,args=` where there is no `/proc` (macOS). A debug server that lets go of its runner (`debugserver` or `lldb-server` after lldb's `detach`, which is how CodeLLDB ends an attach session) exits and leaves the runner going, followed by nobody and without a time limit; both servers start the runner in a process group of its own, so the group of the server's process never reaches it. A case still in progress is reported as a crash. VS Code's CodeLLDB configuration also ends the runner with the session (`preTerminateCommands`: an lldb `script` that kills the process only while it is alive). A `cstudy` killed with SIGKILL cannot do any of this, and the launch's [orphan guard](#process-lifecycle) does it instead: the agent or server, and whatever runs from the launch's private directory |
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
| Start gate | `CountDownLatch` `ready(n)` then `go(1)` | `threading.Barrier(n + 1)`, then a start line: each worker spins until every worker has passed the gate ([why](#python-yields-give-up-the-cpu)) | `asyncio.Event`, set after every task is created | one shared promise, resolved after every worker started |
| Scheduler yield | `Thread.yield()` | `select.select([], [], [], 0)`, which releases the GIL; a thread's first yield, and its first one after each 100 µs, sleeps 1 µs instead, which also frees the CPU ([why](#python-yields-give-up-the-cpu)) | `await asyncio.sleep(0)` | `await new Promise((resolve) => setImmediate(resolve))` |
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
| Python `threads` | Same rule with its scheduler yield, which sleeps at most once per 100 µs | See below |
| Go | Same rule with `runtime.Gosched()` | none: true parallelism |
| Rust | Same rule with `std::thread::yield_now()` | none: true parallelism |
| `async` (Python, TypeScript) | Same rule with macrotask yields | none: a monitoring callback cannot await |

Python `threads`, for the duration of each stress run only:

1. `sys.setswitchinterval(1e-5)`; the previous value is restored at step 8.
2. Unless `python_granularity` is `none`: `sys.monitoring.use_tool_id(3, "cs-stress")`, register one callback for `LINE` (granularity `line`) or `INSTRUCTION` (granularity `instruction`), `sys.monitoring.set_events(3, <event>)`, and `sys.monitoring.restart_events()` at run start.
3. The callback returns `sys.monitoring.DISABLE` for code whose `co_filename` is not the target file. In the target file, and only on worker threads (a `threading.local` flag), it draws from the worker's PRNG and with probability `yield_probability` makes `1 + randrange(max_yields)` scheduler yields.
4. At run end: `sys.monitoring.set_events(3, 0)` and `sys.monitoring.free_tool_id(3)`.

#### Python yields give up the CPU

A Python scheduler yield releases the GIL for a system call that returns at once, `select.select([], [], [], 0)`. A thread's first yield, and its first one after each 100 µs, sleeps for 1 µs instead. The sleep frees the CPU, so on a busy machine a worker waiting for the GIL that the OS was not running gets a turn and takes it. A sleep costs a few microseconds whatever else wants the CPU, since a sleeping thread keeps its scheduler share and wakes on time; at most one per 100 µs keeps that under a tenth of a worker's time. Linux pads every sleep with the thread's timer slack, 50 µs by default, so each worker thread sets its own to 1 ns (`prctl(PR_SET_TIMERSLACK)`), and its 1 µs sleep takes about 5 µs, as on macOS.

Releases alone do not hand the GIL over on a busy machine. The waiting worker is rarely running during the call, and each release wakes its wait before the switch interval runs out, so it never asks the holder for the GIL (CPython asks only after a wait times out). The yielding worker keeps the GIL and can run its whole script alone. For the same reason the workers wait at a start line after the gate: the gate releases them together, but a busy machine wakes them one at a time, and the first could finish before the others asked for the GIL.

Earlier yields:

| Yield | Why it was replaced |
|-------|---------------------|
| `time.sleep(0)` | On macOS a release alone: at load 29 to 88 on 11 cores, the racy `conformance-stress-counter` reference lost no increment in 12 of 100 runs, so 3 of 10 verifies missed the 9 of 10 required; traces showed the workers running one after another (0 to 187 µs, 223 to 459 µs, 483 to 771 µs). On Linux a sleep for the timer slack, 55 to 90 µs at every yield: the slowest correct `read-write-lock` run took 94% of its deadline |
| A busy wait of one switch interval that keeps the GIL, with the start line | It spins even while every other worker is blocked: the slowest correct `read-write-lock` run took 19% to 28% of its deadline on macOS (load 6 to 13) and up to 33% on Linux |
| `os.sched_yield()`, with the start line | It gives up the thread's turn whenever another process wants the CPU: a whole time slice (3 ms) at every yield on Linux, whose scheduler (EEVDF) moves the yielding thread behind the others, and a 10 ms quantum at about one yield in 100 on macOS. A `read-write-lock` run makes about 40,000 yields, so on a busy machine correct runs stalled at their deadline |

Measured in a Linux container (Ubuntu 24.04, kernel 7.0, linux/arm64 on an 11-core M3 Mac) and on that Mac, with CPU hogs (`yes`) for load. Shares are the slowest correct run of 10 to 30 against its deadline; the racy counter's column counts its runs that lost no increment, where `verify` requires at most 1 in 10:

| Machine | `os.sched_yield()` | 1 µs sleep at most once per 100 µs, releases otherwise |
|---------|--------------------|--------------------------------------------------------|
| Linux, 11 CPUs, idle | `read-write-lock` 9%, others 10% or less; racy counter 0 of 30 | `read-write-lock` 12%, others 9% or less; racy counter 0 of 30 |
| Linux, 4 CPUs, 4 hogs | every run of `token-bucket-limiter`, `thread-safe-lru-cache` (`locked-dll`) and `read-write-lock` stalled at its deadline | `read-write-lock` 15%, others 6% or less; racy counter 0 of 50 |
| Linux, 4 CPUs, 8 hogs | every run of `token-bucket-limiter` and `read-write-lock` stalled; the correct counter took 67% | `read-write-lock` 10% to 40% across five series, as the Mac running the container got busier; `token-bucket-limiter` 6% to 28%; racy counter 0 of 70 |
| Linux, 4 CPUs, 16 hogs | stalled runs | `read-write-lock` 12%, others 7% or less; racy counter 0 of 50 (10 of 50 with releases alone) |
| macOS, 11 cores, 22 hogs and other work (load 75 to 215) | `read-write-lock` 81% at the median in one series and stalled in another; `token-bucket-limiter` 43% to 97%; `concurrency-limiter` 30% to 50% | `read-write-lock` 8% to 27%; `token-bucket-limiter` 5% or less; `concurrency-limiter` 30% to 39%; racy counter 0 of 50 |

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
| `9014-conformance-stress-counter` | `atomic` (correct counter), `racy` (reads the count on one line and writes it on the next; TypeScript awaits between them, and Java, Kotlin, Go and Rust yield to the scheduler between them) | `atomic` passes 10 of 10; `racy` fails at least 9 of 10 in every language and variant |
| `9015-conformance-stress-stall` | `never-opens` (`await` or wait on a gate nobody opens) | `stalled`, with `progress` naming the waiting workers |
| `9016-conformance-stress-worker-error` | `throws-at` (a worker op throws at op 100) | `error` with `phase: "worker"` and `op_index` 100 |
| `9017-conformance-stress-sections` | `locked`, `unlocked` (a mutex around `@enter`/`@exit` probes) | `locked`: 0 violations; `unlocked`: violations in at least 9 of 10 runs |
| `9018-conformance-stress-async-determinism` | `interleaves` (Python async, TypeScript) | Two runs with the same seed produce identical run records; different seeds produce at least two distinct records over 10 runs |
| `9019-conformance-stress-leak` | `ignores-interrupt` (threads: a worker spins forever after another worker throws) | `error`, then `restart_requested`; the next case still runs |

## Project jobs

A [project problem](problem-format.md#project-problems) is a folder, not one file, and its native tests run inside the runner. Two kinds of job serve it: a **grading job** (`cstudy submit`, and `cstudy verify` D1 and D3), an ordinary class job whose target is the project, and a **suite job** (`cstudy test`, and D1 and D9), which runs the project's native test framework in-process. The Python, TypeScript and JVM (Java and Kotlin) runners support both. The Go runner supports both too, running the tests as a child process ([Go project jobs](#go-project-jobs)). The Rust runner runs grading jobs, and `cstudy` runs a Rust project's suite itself, one process per test ([Rust projects](#rust-projects)).

A service project runs in Docker and is graded over HTTP by the core, with no runner job. See [service projects](service-projects.md#http-grading).

### Capability

`hello.features` lists `project` and `suite` when the runner supports them, and `clock` and `project-stress` when it grades [virtual-clock projects](#virtual-clock-and-stress-in-project-jobs) and project stress cases. `cstudy` refuses a project job to a runner that does not list the feature it needs, as an environment error (exit 4). The JVM runner lists `stress`, `project` and `project-stress` always, and `suite` when a test framework host is on its classpath: a project's test runtime classpath holds `cs.suite`, the classpath of a single-file problem does not. It lists `clock` only when `cs.coroutines` is on its classpath. The Go runner lists `clock` in the test binary of a virtual-clock project, and in the runner of a project that does not compile, which answers every job with the compiler's errors. The Python runner lists `clock` always: its loop is `cs_support.virtual_clock`, in every workspace venv. The TypeScript runner lists `clock` always: `node:test` ships with Node. The Rust runner lists `project` and `project-stress` (and `stress`), not `suite`: no runner process hosts a Rust suite. It lists `clock` in the harness of a virtual-clock project, which turns on the runner crate's `clock` feature, and only there.

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

A Java or Kotlin project folder is a Gradle build of its own ([starter](problem-format.md#starter)), which applies the `cs.project` plugin of the runtime's `runners/jvm` build: the [release level](#the-jdk-and-the-release-level) of the selected JDK, JUnit Jupiter for the tests and kotlin.test on JUnit 5 with Kotlin, `cs.runner` on the runtime classpath, and its JUnit Platform host `cs.suite` on the test runtime classpath ([ADR 0014](../decisions/0014-project-problems.md#java-and-kotlin-spike-k4)). A Kotlin project on the virtual clock also applies `cs.coroutines`: `kotlinx-coroutines-core` and `kotlinx-coroutines-test` on its main and test classpaths, and the runner's bridge to their test scheduler, the module `cs.coroutines`, on its runtime classpath ([virtual clock](#virtual-clock-and-stress-in-project-jobs)).

| Item | Rule |
|------|------|
| Command | `jvm/gradlew -p <root> -q --console=plain --no-watch-fs --offline <task>`, run in `jvm` like every JVM build, so it uses the workspace's Gradle and its daemon, on [the selected JDK](#the-jdk-and-the-release-level). `--offline`: a project build never reaches the network; `cstudy doctor --fix` caches what it needs |
| Tasks | A suite job builds `csClasspath`: the main and test classes, and both runtime classpaths, in `build/cs/main-classpath.txt` and `build/cs/test-classpath.txt`. A grading job builds `csMainClasspath`: the main classes and `build/cs/main-classpath.txt` only, so a test file that does not compile, such as a level's generated tests before its methods exist, never blocks a submission |
| Locked levels | `-Pcs.exclude=<path>,...` names the generated test files of the levels above `cstudy test --level N`, relative to the root, and the plugin leaves them out of the test compile: they may call methods that do not exist yet. The runner reads no `exclude` |
| Concurrent `cstudy` processes | One process at a time builds a folder and copies what it built: an exclusive `flock` on `.cs/build/jvm-locks/project-<folder name>-<digest of its absolute path>.lock`, held around the build, the read of the classpath file and the copy, with the runtime lock of [JVM build details](#jvm-build-details) inside it. Two folders, or a folder and a single-file problem, build side by side |
| Per-run class copy | As for single-file problems: the classpath entries below the folder's `build/` and the runtime's jars are copied into `.cs/build/jvm-runs/<pid>-<random>/`, which the run removes when it ends |
| Compile errors | Lines of the compiler's output that mention the folder's `src/`, with their indented context, at most 40, paths relative to the folder (Gradle prints them twice, the second time under its failure report: the first copy is kept): a grading job reports them as its `load_error` (type `CompileError`), so the submission is stored with every graded case errored and `cstudy submit` exits 2; a suite job reports them as the suite's `load_error`, and `cstudy test` lists them and exits 2, as for code that does not compile in a single file; each error is a [diagnostic](cli.md#diagnostics) at its file and line in the folder |
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
| `framework` | `pytest`, `node-test`, `go-test` or `junit-platform` (Java and Kotlin); a Rust suite is `libtest`, which `cstudy` runs itself ([Rust projects](#rust-projects)) |
| `root` | The project root |
| `exclude` | Files, relative to the root, that are not run: the generated files of levels above `cstudy test --level N`. On the JVM the build has already left them out of the test compile |
| `select` | Test ids to run (`cstudy test --case`); empty: every test the framework discovers |
| `skip` | Test ids not to run, set on a restart |

A suite job has no `cases`: the framework discovers the tests. Python discovers them as pytest does from the root, under the project's `pyproject.toml` (`testpaths`, `pythonpath`, `addopts`); TypeScript takes the files `node --test` finds from the root with its default patterns; the JVM discovers them in every directory of its classpath, which are the project's main and test class directories, never in a jar.

| Item | pytest | `node:test` | `junit-platform` |
|------|--------|-------------|------------------|
| Host | `pytest.main([...])` on the `cs-runner-cases` thread, with `--rootdir <root>`, plugin autoloading off (`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`), `-p no:cacheprovider`, pytest's own capture off, and a plugin of the runner's that writes the events | `run({ files, isolation: "none", concurrency: 1 })` in the runner's process, its `test:start`, `test:pass` and `test:fail` events turned into protocol events | The JUnit Platform Launcher (`LauncherFactory.openSession()`) on the `cs-runner-cases` thread, with parallel execution off whatever a `junit-platform.properties` says, and a `TestExecutionListener` that writes the events. `cs.runner.Main` finds the host, `cs.suite`, with `ServiceLoader` |
| Test id | pytest's node id: `tests/test_level_1.py::test_ex1` | `<file relative to the root>::<test name>`, nested names from the outermost `describe` joined by ` > ` | As for every suite, the file first, relative to the root, then the method: `src/test/java/bank/Level1Test.java::ex1`. The file is the class file's `SourceFile` attribute (javac's and kotlinc's both) under the class's package, so a Kotlin file named otherwise is found too. A nested class, or a top-level class not named like its file, comes before the method, joined by ` > ` (`src/test/kotlin/bank/BankTests.kt::Deposits > refusesNegative`), and each parameterized or dynamic invocation adds `[n]` (`...RateTest.java::rounds[2]`). A class reported on its own is its file, or its file and class names |
| `skip` | Left out by exact node id in the runner's plugin (pytest's `--deselect` matches prefixes, so it is not used) | Left out by exact id: a `beforeEach` hook of the runner's throws before the body of a test that `skip` lists or `select` does not name, and nothing is reported for it (with isolation `none`, Node reads name patterns only from its own command line) | | Left out by exact id, and by class: every test of a class whose id is in `skip`, since a class whose setup failed, or a disabled one, was reported once under its own id, and its setup must not run and report it again. A parameterized or dynamic test with an invocation in `skip` is left out whole, since running it again would report its earlier invocations a second time |

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
| `go.work` per root | `.cs/build/go/project/<root>/go.work`, where `<root>` is the project root relative to the workspace (`projects/bank-project-go`): `use` of the build module `csbuild` and of the root, and `replace` of the runner module `cstudy` and of each vendored module with the runtime's copies. A `replace` in a `go.work` outranks the folder's `go.mod`, so a reference's build copy, deeper than `projects/<slug>/`, builds too. Its `go` line is the higher of 1.25, the `go` line of the runner module, and the folder's `go.mod` |
| Grading binary | `cmd/project/<snake_slug>/main.go` imports the entry's package as target `user`: `<module>/<directory of project.entry>`, or `<module>` for an entry at the root, with the module read from the root's `go.mod`. The registration (`New<Class>`) and the thunks of the graded levels' methods, generated in `.cs/build/go/project/<root>/`, enter that package through `go build -overlay`, so nothing is written to the folder. Built as `bin/project/<snake_slug>` with `GOWORK` naming the root's `go.work`, and launched in the root. A virtual-clock project's grading binary is a test binary instead (below) |
| Virtual-clock grading binary | `go test -c -json -vet=off -overlay=F -o bin/project/<snake_slug> <import path>` of the same package, launched as the grading binary is. `-vet=off` keeps the build `go build`'s: `go test -c` vets a package, so a vet finding would fail it. The overlay adds the registration and the thunks, leaves the package's own `_test.go` files out (one that does not compile never blocks a submission, and none can declare a `TestMain` of its own), and adds the generated `zz_cs_main_test.go`, whose imports take names of their own (`csrunner`, `cstesting`, `cssynctest`) so that no identifier of the package clashes with them. Its `TestMain` calls `runner.MainOnClock` with the registration, the thunks and `m.Run`: the runner reads its flags, leaves the test framework only `-test.run=^TestCsGrading$`, and runs the tests. The one test, `TestCsGrading`, hands `runner.GradeOnClock` the clock: `Bubble`, which runs a case in a `synctest.Test` of its own, and `Settle` (`synctest.Wait`); `@advance` is `time.Sleep` and `@now` `time.Since` inside the bubble, so the runner package does not import `testing`. The case's output is captured from outside the bubble, since a goroutine that reads a pipe is not durably blocked, and its `duration_ns` is the real time of the whole case. A recovered deadlock panic is the case's `stalled`: `deadlock: all goroutines in bubble are blocked` at the operation in progress, and `deadlock: main bubble goroutine has exited but blocked goroutines remain` at the last operation, `the case ended with goroutines still blocked`, unless the case had already failed, which keeps its error. The virtual time of the reason is the bubble's clock, which the runtime's deadlock error carries and the runner reads by reflection (`testing/synctest` has no other way once every goroutine of the bubble is blocked for good); a Go release whose error does not carry it leaves the time out. Either way the goroutines stay blocked, so the runner writes `restart_requested` and the next case runs in a fresh process. A goroutine that waits on a held `sync.Mutex` is not durably blocked, so the clock stops and the case meets the hang guard. The binary links `testing`, and its warm build is within the range of `go build` ([ADR 0017](../decisions/0017-async-project-problems.md)). Other projects keep `go build`, and a project that does not compile gets the plain runner of `runner.MainBuildFailed` |
| Grading target | `{"compiled": "user"}` in a job of kind `project`, otherwise the class job of [Grading job](#grading-job) |
| Compile errors | Errors only in the registration or thunk files: the second pass and the runner's `load_error` of [Go build details](#go-build-details). Errors in the project's files: the binary is built again without the project, and the runner reports a `load_error` of type `CompileError` whose message is the compiler's lines with paths relative to the root (at most 40) and whose trace is the first error's `file:line`, so `cstudy submit` stores a submission whose code does not load and `cstudy verify` D1 and D3 name the errors. A failure with no diagnostics in the project is an environment error (exit 4), as for single files |
| Suite binary | `cmd/suite/main.go`, the runner with no target, built as `bin/suite/cs_go_suite`; the first suite build of a workspace also compiles `testing` and `testing/internal/testdeps`, so that a cold build cache does not keep the first `go test` silent past the CLI's idle limit. It is launched in the root with the fixed environment of [Go build details](#go-build-details), `GOWORK` naming the root's `go.work`, and the user's platform settings (`GOOS`, `GOARCH`, `GOEXPERIMENT`, `GOFIPS140` and the instruction-set levels) set empty, which the go command reads as unset |
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
| Debug | `cstudy test --debug` runs one package under Delve: the package of the selections when they name files of one package, else the package of the generated test files (`project.tests`). The runner builds its test binary with `go test -c -gcflags=all=-N -l` into the launch's private directory, starts `dlv exec --headless --listen=127.0.0.1:<port> --api-version=2 --wd <package directory> <binary> -- -test.v=test2json -test.count=1 -test.timeout=0 -test.paniconexit0 [-test.run R] [-test.skip S]`, copies Delve's `API server listening at:` line to its own standard output for the [ready line](#debug-mode), and pipes the rest through `go tool test2json -t -p <import path>`. A package that does not build is reported as above, and nothing waits for a debugger; a test binary that ends early is reported as above and its package does not run again. Delve is found, and required, as in [debug mode](#debug-mode). A Delve that listens and then refuses the test binary because its Go is older than the Delve debugs (`Go version go1.24.13 is too old for this version of Delve (minimum supported version 1.25, ...)`) ends the session as an environment error (exit 4) that shows Delve's own output, as for a single file, whatever the suite reported |

### Rust projects

A Rust project folder is a crate of its own ([problem-format](problem-format.md#rust-projects)). Both of its jobs build in a Cargo workspace of the project's own, with the dev profile, and the build never writes into the folder ([ADR 0014](../decisions/0014-project-problems.md#rust-spike-k6)).

| Item | Rule |
|------|------|
| Build workspace | `.cs/build/rust-projects/<slug>/`: `Cargo.toml`, a workspace whose only member is `harness/`, with the [profiles](#rust-build-details) pinned as in `.cs/build/rust`; `harness/Cargo.toml`, the package `project_<snake_slug>` with the bin target of the same name, depending on the project crate by path as `user = { package = "<crate>", path = "<root>" }`, on `cs_runner` and `cs_support`, and on `rust_decimal` and `chrono` as the other harnesses do; `harness/main.rs`, the bridge. The crate is the `[package] name` of the root's `Cargo.toml`, read on every build. One workspace serves every root of the problem (the folder, D1's starter, D3's reference), so its manifest names the root of the last build |
| Settings | As in [Rust build details](#rust-build-details): offline, `--target <host>`, the vendored source as `--config`, the user's Cargo variables removed, and `CARGO_TARGET_DIR=.cs/build/rust/target`, shared with the single-file builds. The profile is dev, pinned as for `cstudy test --debug`: the suite and the grade then share the crate's compiled code, and a grade after a suite run compiles only the harness. `CARGO_HOME` is the build workspace's own `cargo-home/`, since builds that share a `CARGO_HOME` wait on its package-cache lock; the vendored source needs nothing from it, and the user's `config.toml` stays out |
| Concurrent `cstudy` processes | The generation and the build hold an exclusive `flock` on `.cs/build/rust-projects/<slug>/.cstudy.lock` and the shared runtime lock of [Rust build details](#rust-build-details); each run launches private copies of the binaries it runs, in `run/<pid>-<random>/` under the build workspace, removed when the run ends |
| Grading job | `cargo build -p project_<snake_slug>`, then the harness binary as any Rust runner: `{"compiled": "user"}`, launched in the root. The bridge is generated from the graded signature, so a method of a locked level is never called, and the user's crate is the dependency `user`, not a `#[path]` module. Its `Target.file` is the root with a final `/`, so a trace keeps every frame in a file under the root, named relative to it (`src/ledger.rs:12 in Ledger::post`). Compiler errors in the root's files: no run, and every graded case gets the `load_error` `CompileError` of [JVM project builds](#jvm-project-builds), `the project does not compile`, whose trace is the compiler's lines (at most 40), paths relative to the root, so `cstudy verify` D1 and D3 name the first error (`src/lib.rs:4:5: error[E0425]: cannot find value ...`). Errors only in the bridge are `load_error`s as for single files, naming `src/lib.rs` for the crate |
| Suite build | `cargo build -p <crate> --lib --tests --keep-going --message-format=json`: the library's unit tests, each integration test under `tests/`, and the unit tests of any bin target. `--keep-going` builds every target that compiles when another does not |
| Test targets | Each built test binary, by the `src_path` of its target relative to the root (`src/lib.rs`, `tests/level_1.rs`), in path order. The targets of `exclude` (the generated files of locked levels) are neither listed nor run, and their compiler errors are left out. A target with compiler errors is one `error` result whose `case_id` is that path, of type `CompileError`, whose message is the first error (`tests/broken.rs:3:22: error[E0308]: mismatched types`) and whose trace the rest, paths relative to the root; a target that the build left out because a target it needs did not compile (an integration test whose library does not build) reports nothing of its own |
| Listing | `<binary> --list --format terse`, the lines `<name>: test`, in its order; a binary whose listing fails is one `error` result for its target |
| Test id | `<target path>::<libtest name>`: `tests/level_1.rs::ex1`, `src/lib.rs::ledger::tests::posts_twice`. `select` and `skip` match ids, or their last part, as for the other frameworks. The id names the target, not the file that declares a unit test, so `cstudy test` finds that file for the test's [origin](cli.md#project-problems) from the libtest name's module path, as `mod` declarations find files: the innermost module with a file of its own in the folder, `<module>.rs` or `<module>/mod.rs` from the target's directory (`ledger::tests::posts_twice` is in `src/ledger.rs`, or `src/ledger/mod.rs`, or `src/ledger/tests.rs` when that exists), else the target itself, for a test of the crate root or of a module written inline in it. `#[path]` attributes are not followed |
| Run | Each test as a process of its own, one at a time: `<binary> --exact <name> --nocapture` in the root, with `RUST_BACKTRACE=0`, standard output and standard error captured together, and a process group of its own, which an [orphan guard](#process-lifecycle) kills if `cstudy` dies first |
| Output | What the test printed, without libtest's own lines and without the panic message, which goes to `message`; the 4 KiB limit of [Execution environment](#execution-environment) |
| Hang guard | The test's process group is killed after the hang guard of the [suite rules](#suite-job); the test is `timeout`, and the next test runs. Nothing restarts, since nothing else was in that process |

| Exit of the test's process | Result |
|----------------------------|--------|
| 0, libtest counting `1 passed` (including a `should_panic` test that panicked as it should) | `ok` |
| 0, libtest counting `1 ignored` | `skipped`, `message` the reason of `#[ignore = "..."]`, or `ignored` |
| 101 | `failed`: `message` is the panic's message, then `at <path>:<line>:<column>` relative to the root (`assertion \`left == right\` failed`, `left: 3`, `right: 4`, `at tests/level_1.rs:9:5`); without a panic, what libtest printed for the failure (`note: test did not panic as expected ...`, or the `Error: ...` of a test that returned an `Err`). Every panic is `failed`, the `todo!()` of a starter's method included: libtest does not tell an assertion from another panic |
| Any other exit, or a signal (an abort is 134, 128 plus `SIGABRT`) | The test crashed (`Crashed` with that code and the last 20 lines of its output); the next test runs |

Doctests are not run. The report's runner is `rust`, with the `rustc` version as its runtime.

| Debug | Rule |
|-------|------|
| What runs | One test, in its own process under Rust's [debug server](#debug-mode): the first test the suite would run, after `--case`. The others do not run, and the report says so (`a debug run of a Rust project runs one test; pick it with --case`) |
| Command | `debugserver --stdout-path=<scratch>/stdout.txt --stderr-path=<scratch>/stderr.txt --named-pipe <scratch>/debug-port 127.0.0.1:<port> -- <binary> --exact <name> --nocapture`, in the root, with the private copy of the test binary; the server holds the test at its entry point until the IDE connects with `gdb-remote`, as for single files. `lldb-server` (Linux) runs as `lldb-server gdbserver --named-pipe <scratch>/debug-port 127.0.0.1:<port> -- <binary> --exact <name> --nocapture --logfile <scratch>/libtest.log`, without the output options. Breakpoints in the project's code and in the test both stop |
| Result | With `debugserver`, read from the test's output, which the server writes to those files: libtest's `test result:` line counts the test passed, failed or ignored, and its absence means the test crashed. The exit code is the debugger's, not the test's. `lldb-server` on Linux has no such option and sends the test's output only to the debugger, so the test writes libtest's log (`--logfile`), whose line `ok <name>`, `failed <name>` or `ignored <name>` gives the outcome: `ok`, `failed` or `skipped`, and no line means the test crashed. That log holds no output and no panic: a failed test's `message` says `the test failed; its panic message went to the debugger, not to cstudy` (libtest's own note for a failure such as a `should_panic` test that did not panic), and `output` is empty. Breakpoints stop as on macOS |
| Watchdog, stopping | As in [debug mode](#debug-mode): no time limit; Ctrl-C, SIGTERM and SIGHUP kill the server's process group and every process running from the launch's private directory |

### Virtual clock and stress in project jobs

The virtual clock and the stress cases of [project problems](problem-format.md#asynchronous-code-and-the-virtual-clock) are additive to protocol 1: existing jobs, events and exit codes keep their meaning, and `protocol` stays `1` ([ADR 0017](../decisions/0017-async-project-problems.md)). The clock reaches the runners one language family at a time ([scope and order](../decisions/0017-async-project-problems.md#scope-and-order)).

| Item | Rule |
|------|------|
| Capability | `hello.features` gains `clock` (the virtual clock, its harness operations and asynchronous methods) and `project-stress`. `cstudy` refuses such a job to a runner without them as an environment error (exit 4), as it does for `project` and `suite`, and `cstudy doctor` prints them after the protocol |
| Request | A virtual-clock grading job has `"clock": "virtual"`, marks each asynchronous method of its `signature` with `"async": true`, and holds the harness operations in the `ops` of its cases. `"clock_seed"` names the seed by which a runner that shuffles simultaneous timers (Python) orders them: absent, it is 0, as in `cstudy submit`; D10 sends 1 to 9 for its other runs. A runner that has no seeded order ignores it. A project with stress cases sends the runs of the graded levels' stress cases in the same job, after its sequential cases, as a concurrent job does ([Concurrent jobs](#concurrent-jobs)), and names the job's `model`; `cstudy` keeps each run's `level`, which the request does not carry, since runners echo case ids and never parse them |
| Operations | Each case follows the [semantics of the virtual clock](problem-format.md#semantics-of-a-case-on-the-virtual-clock): the runner calls the operation, awaits an asynchronous result, then settles before the next. `@advance` and `@spawn` output `null`, `@join` the call's result, and `@now` the virtual milliseconds since the case started |
| Deadlock | An operation that waits while no task can run and no timer is due ends the case at once as `stalled`, with `op_index` (the operation), `reason` (`op 4 (@join r1): deadlock at 3000 ms`) and `partial_output`, as for `error`. A wait on what the clock cannot see never lets time move and meets the hang guard as `timeout` |
| After a deadlock | A `stalled` case that leaves goroutines (Go) or threads behind makes the runner write `restart_requested` and exit 3, so the next case starts in a fresh process. These restarts do not count against the 3 crash restarts, as for stress runs; a `timeout` still counts. Python drops a deadlocked case's tasks as `asyncio.run` does, Rust drops the case's runtime and its tasks with it, and Kotlin cancels a case's coroutines, none of which holds a thread, so their next case runs in the same process; any case on the clock that leaves a thread running, deadlocked or not, makes it ask for the restart (`1 threads of strand are still running`) |
| Hang guard | Per case, as for every class job: the case's `hang_guard_ms`, else `limits.hang_guard_ms`, else 10 s. A correct virtual-clock case takes milliseconds, so an author lowers `limits.hang_guard_ms` to a few seconds. There is no per-operation timeout and no bench; after 3 restarts the remaining cases are `not_run`, as today |
| Process lifecycle | Unchanged: a runner starts in a process group of its own with an orphan guard, and starts no process of its own ([Process lifecycle](#process-lifecycle)). Go's test-binary harness is the runner process. SIGINT and SIGTERM end a submission as before |
| Runs | A virtual-clock case runs once in `cstudy submit`, since its only nondeterminism is Go's shuffle of simultaneous wake-ups. `cstudy verify` runs every case 10 times on the reference (D10) |
| Debug | `cstudy test --debug` runs the native tests on the virtual clock, and a breakpoint does not move it, so no timeout fires while you inspect the code |

Each language uses the virtual time its own ecosystem tests with, so the generated tests, your own tests and the grader run on one clock:

| Language | Grading | Libraries and offline use |
|----------|---------|---------------------------|
| Go | A test binary with a `synctest.Test` per case ([Go project jobs](#go-project-jobs)). Time is the `time` package inside the bubble; simultaneous wake-ups are shuffled at random | The standard library, from Go 1.25, the first release with `synctest.Test`. A virtual-clock starter's `go.mod` says `go 1.25`, and so does the folder's `go.work` |
| Python | Each case runs in `asyncio.run(..., loop_factory=VirtualClockLoop)`, the loop of the module `cs_support.virtual_clock`, from the constructor on: its `time()` is virtual and starts at 0, its selector moves the clock to the next timer instead of sleeping, it breaks ties between timers due within 1 µs of each other by a shuffle seeded with `clock_seed`, and it raises a deadlock when no callback is ready and no timer is due. While a call it handed to a thread (`asyncio.to_thread`, `run_in_executor`) runs, or a file or socket is registered, the clock stands still and the loop waits for real. Every awaitable result is awaited, of a declared `async` method or not; `@spawn` makes a task of an awaitable (a plain result is joined as it is), and an exception or cancellation in a task is the error of its `@join`. `duration_ns` is the real time of the whole case. Code that reads `time.monotonic()` or `time.time()` reads the real clock | None new: `cs_support` is installed in every workspace venv from the runner runtime, which `cstudy` refreshes, so grading and tests share one implementation and no workspace needs a migration. The pytest plugin in the same module runs `async def` tests on the same loop; the starter's `pyproject.toml` loads it with `-p`, since the runner turns plugin autoloading off. Seed 0 in grading and in your tests, seeds 0 to 9 in D10 |
| TypeScript | `node:test`'s `mock` timers (`setTimeout`, `setInterval` and `Date`), driven by `runners/typescript/lib/virtual-clock.ts`, enabled at 0 for each case from the constructor on and reset after it: it records the due time of each timer that `setTimeout`, `setInterval` (global or from `node:timers`) and `setTimeout` from `node:timers/promises` set, forgets one when it fires or is cleared, ticks to the next one, and lets promise continuations run (one real macrotask) before the following one. It calls `syncBuiltinESMExports()` after enabling and after resetting the mocks, so a static import of `node:timers/promises` is mocked. Timers due at the same instant fire in the order they were set, so `clock_seed` changes nothing. The clock sees only the mocked timers: a wait that none of them can end is a deadlock at once, even one that real I/O or a timer function stored before the case started would end. Every thenable result is awaited, of a declared `async` method or not; `@spawn` follows a call's result from the moment it starts, so a rejection is handled before `@join`, whose error it is. `duration_ns` is the real time of the whole case | None new: `node:test` ships with Node 24. The same file, copied into the starter as `tests/virtual-clock.ts`, serves the generated tests and yours, since a project folder reaches no `#support` module; S15 keeps the copy byte-identical to the template's |
| Kotlin | A bridge in the runner module `cs.coroutines`, written in Kotlin, implements `cs.runner.ClockHost`: `cs.runner.Main` finds it with `ServiceLoader` on the main runtime classpath of a project that applies the `cs.coroutines` plugin, as it finds `cs.suite`, decodes each case's operations and records their outputs, and the bridge runs them. Each case runs on a `TestCoroutineScheduler` of its own, from the constructor on, as one coroutine on a `StandardTestDispatcher`, as a `runTest` body runs: it makes each operation's call in turn, a `suspend` method's with the caller's `Continuation` as the extra last argument of its JVM signature, and calls `runCurrent()` after each. `@advance` is `advanceTimeBy` then `runCurrent()`, `@now` the scheduler's `currentTime`, and `@spawn` an `async` under a supervisor, so a task's failure is the error of its `@join`. The scheduler runs every coroutine of the case on the case's thread, in the order of their virtual times, until nothing is due (`advanceUntilIdle`): a case that has not ended by then waited on something nothing can end, a deadlock, and a case whose calls left coroutines active in their scope, as children of the case, is `stalled` with `the case ended with coroutines still active`, as `runTest` fails such a test. The case's coroutines are then cancelled. Tasks due at the same instant run in the order they were scheduled, so `clock_seed` changes nothing. The clock sees only the test scheduler: code that moves to another dispatcher (`Dispatchers.Default`, `Dispatchers.IO`) runs on the real clock, and a wait that only such code can end is a deadlock at once, where `runTest` would wait for real. The code reads the clock through the scheduler in its coroutine context (`currentCoroutineContext()[TestCoroutineScheduler]`, whose `timeSource` measures the virtual time); `duration_ns` is the real time of the whole case | `kotlinx-coroutines-core` and `kotlinx-coroutines-test` at the release the pinned Kotlin supports, in the runners' version catalog (1.11.0). The plugin adds both to the main source set, so the code can read the scheduler's time, and the bridge to its runtime classpath; the starter applies it; the Kotlin warm-up project of `cstudy doctor --fix` applies it too, so they are cached for offline builds as JUnit is ([ADR 0014](../decisions/0014-project-problems.md#java-and-kotlin-spike-k4)). Their class files, and the module's at release 21, load on every JDK of ADR 0016's range |
| Rust | The bridge registers the entry class as `Entry::Clock`, and the runner crate's `clock` feature (`cs_runner::virtual_clock`) runs each case on a tokio runtime of its own, current-thread and built with its clock paused (`start_paused`), from the constructor on. Each operation is a `block_on` on that runtime: the call, an `async fn` awaited and any other method called inside it, so code can `tokio::spawn` and read the clock, then the settle step. tokio has no call that waits until every task waits, but its park hook runs exactly then: the current-thread scheduler calls `on_thread_park` when no task is ready, none yielded and the `block_on` future was not woken, and only that park moves a paused clock, so settling waits to be woken by it; a timer due at that instant has fired already, since tokio fires one registered at or before the current instant at once. `@advance` is `tokio::time::sleep` then settling, so tokio moves the clock to each due timer on the way (auto-advance); `@now` reads tokio's `Instant` since the case started; `@spawn` hands the call to `tokio::spawn` and `@join` awaits its `JoinHandle`, a task's panic being the error of its `@join`. A spawned call holds the instance, so from the first level whose cases `@spawn` a task, or have stress cases, the bridge shares the entry class as for stress (`&self` methods, `Send + Sync`), and a spawned call's future and result must be `Send`. A wait races a sentinel timer at least 2^35 ms (about 398 days) ahead, at a multiple of 2^30 ms, where tokio's timer wheel fires it in one step: when it fires first, every task waited while no other timer was due, and the case is `stalled` at the virtual time of the last idle park. The case's runtime is then dropped, and with it every task still pending, as a dropped runtime drops them, so the next case runs in the same process; dropping it waits for a blocking task (`spawn_blocking`) still running, which therefore meets the hang guard. While a blocking task runs, tokio holds the paused clock still and waits for real, and settling does not wait for it. Tasks due at the same instant run in the order they were scheduled, so `clock_seed` changes nothing; `tokio::select!` polls its ready branches in a random order unless it is `biased;`, so D10 can see a tie that a `select!` decides. Code reads time through `tokio::time::Instant`; `std::time::Instant` reads the real clock. `duration_ns` is the real time of the whole case | tokio 1.53.3 with `macros`, `rt`, `sync`, `test-util` and `time`, [vendored](#rust-build-details): the newest release whose MSRV is at most cstudy's Rust 1.80, declared exactly as `rust_decimal` and `chrono` are, by the runner crate behind `clock` and by the starter's `Cargo.toml`, so the crate and the runner share one copy. The harness of a virtual-clock project turns `clock` on, and a suite build keeps the harness as the last grading built it, so no build of another problem compiles tokio |
| Java | No virtual clock and no asynchronous methods: `java.time`, `Thread.sleep` and the executors read the real clock, and nothing in the JDK replaces it without the code's help. Java projects get stress cases | |

#### Stress in project jobs

| Item | Rule |
|------|------|
| Job | The grading job carries a project's stress cases as a concurrent job carries its own, and each runner runs them with its existing stress code on the project's entry class. A grading job with stress runs names its `model` (`"model": "threads"` or `"async"`), and a runner reads a project job with a `model` as a concurrent job whose class comes from the project, as its grading job loads it; its sequential cases run as the grading job's do, on the virtual clock when it has one, and its stress runs on the real clock. A grading job without stress runs (a level below the first stress case, or `cstudy verify` D10) names no `model`. A runner without `project-stress` in `hello.features` cannot run such a job (exit 4, `runner <lang> does not support project problems with stress cases`) |
| Python | Line and instruction perturbation yields in every file under the project root, where a single file's run yields in the target file only. TypeScript, and Python with asynchronous methods, use the `async` model |
| JVM | Each thread kind that `jvm_threads` lists runs. A stress case and a broken overlay must hold on every JDK of the problem's range, as [ADR 0016](../decisions/0016-jdk-range.md) requires. A worker calls a Kotlin `suspend` method through the bridge `cs.coroutines`, in `runBlocking`, which blocks the worker's thread until the call returns and waits on the real clock; the threads model stays the JVM's only one, so Kotlin coroutines meet stress as callers on threads |
| Go | The stress workers keep reflection, as for single files |
| Rust | The bridge registers the entry class as concurrent, so its methods take `&self` from the level that adds stress cases, or the first level whose cases `@spawn` a task on the virtual clock, and a `&mut self` method is a load error that says why (`cannot borrow ... as mutable ...; the worker threads of the stress cases or the tasks of @spawn share the instance, so its methods take &self, not &mut self`). Below that level it owns the class, as for any project. A grading job without stress runs at or above that level (D10) runs its cases on the shared class. On the virtual clock, a worker thread calls an `async fn` and blocks until it returns, on a current-thread runtime of its own on the real clock, as Kotlin's workers call `suspend` methods in `runBlocking` |
| Broken overlays | `cstudy verify` builds each in `.cs/build/projects/<slug>/broken-<id>/`: the starter, the reference's overlay, then the broken overlay |
| Hang guard | A stress run keeps `deadline_ms` and a hang guard of `deadline_ms + 5000` ([Hang guard and restarts](#hang-guard-and-restarts)) |

## Stub generation

| Step | Rule |
|------|------|
| Source | `StubGenerator` for the language renders the signature with the mapping table and naming rules from [problem-format](problem-format.md#type-dsl) |
| Destination | Python `python/practice/<snake_slug>.py`; TypeScript `typescript/practice/<slug>.ts`; Java and Kotlin `jvm/<lang>/src/main/<lang>/practice/<snake_slug>/<Solution or ClassName>.<ext>`; Go `go/practice/<snake_slug>/<snake_slug>.go` in `package <snake_slug>` ([Go file names](#go-file-names)); Rust `rust/practice/<snake_slug>.rs` |
| Body | Python `raise NotImplementedError`; TypeScript `throw new Error("Not implemented")`; Java `throw new UnsupportedOperationException("Not implemented")`; Kotlin `TODO("Not implemented")`; Go `panic("not implemented")`; Rust `todo!()`. Constructors are empty (Go: `return &LRUCache{}` from `NewLRUCache`; Rust: `LRUCache {}` from `pub fn new(...) -> Self`). Rust methods take `&mut self`, or `&self` in a concurrent problem, whose instance the worker threads share |
| Header | The [starter header](problem-format.md#starter-header): title, summary, statement path and run command, over several lines. The title and summary wrap between words at 68 characters of text; a path or the command is never split. Python writes a docstring and the other languages write `//` lines. `cstudy` never rewrites an existing file, so a file started earlier keeps its header |
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
| Project (Python, TypeScript, Go, Rust, Java, Kotlin) | `.cs/build/projects/<slug>/<approach>/`: a copy of `starter/`, then of the overlay `solutions/<approach>/`, then the generated test file of every level; synced to the problem's files on every run (below) | None; run as a [project job](#project-jobs) in that root, which a Java or Kotlin copy builds with its own Gradle files, finding the workspace by walking up |
| Rust | `.cs/build/rust/ref/<snake_slug>/<approach_snake>.rs` | None: reference files are written like the stub (`pub fn`, or `pub struct` with `impl`) and copied unchanged. Each enters the problem's harness crate as the `#[path]` module `ref_<approach_snake>`, so compiler errors name the copy |

A project's copy, and D1's copy of its starter in `.cs/build/stubs/projects/<slug>/` (the starter with level 1's generated test file) are synced, not rebuilt from an empty folder. Each run writes a file only when its content differs, so an unchanged file keeps its modification time, and deletes every other file or link and every directory left empty, so a file removed from the problem never lingers to give a false pass. What build tools wrote there stays: the untracked entries of a [project folder](installation-and-workspaces.md#project-folders), such as `build/`, `.gradle/` and `.kotlin/`, where Gradle keeps the classes and the configuration cache, and `target/`. A Java or Kotlin project therefore builds only what changed on the next `cstudy verify`, and Cargo, which compares timestamps, recompiles an unchanged Rust copy no more; the go command caches by content, so a Go copy builds the same either way. A link at the copy's path, or on the way to a file in it, is removed, never followed.

### Go file names

The go tool ignores a file whose name ends in `_<GOOS>`, `_<GOARCH>` or `_test` (before `.go`), which would leave the package without its function (`SymbolNotFound`). `layout.go_file_name` therefore appends `_code` to any such stem, for the practice file (`go/practice/sort_test/sort_test_code.go`) and for materialized references and broken references (`sort_windows/sort_windows_code.go`). Package names, directories and the `solutions/<approach>.go` files keep their plain names; only the name of the file the toolchain reads changes.

For JVM bench the classpath joins the user's `practice.*` classes and the `ref.*` classes; package names never collide.

## Conformance suite

`runners/conformance/` holds fixture problems in the normal problem format whose reference approaches are identity functions (return the argument unchanged) for every DSL type, plus fixtures for error paths: exception, `invalid_output`, missing symbol, hang, user printing to stdout, `ref_of`, `output_from`, `no_alias_with`, cyclic ListNode input, and decimal and date arithmetic (inputs that keep their scale, canonical outputs, rounding modes, days across leap years). `cstudy verify --conformance` runs each fixture in every language its `meta.yaml` lists and also compiles every generated stub; a runner that does not support a feature yet leaves the fixture's languages without it (Go lists 9001 to 9017 and 9019 to 9021, Rust the same except 9006 and 9010, which [S13](authoring.md#static) keeps out of Rust). It is a Phase 0 exit criterion and must pass before any runner change merges.

Project fixtures, each listing its one language: `9022-conformance-project-python` and `9023-conformance-project-typescript`, two-file projects whose entry imports a sibling module by package path and by relative path (grading); `9024-conformance-suite-pytest` and `9025-conformance-suite-node-test`, suites with a test that passes, one that fails an assertion, one that raises, one that hangs, one that prints and one that ends the process (suite statuses, output capture, hang guard and restart). `expectations.json` gains per-test outcomes for suite fixtures. Go adds `9030-conformance-project-go`, a project whose entry's package imports a subpackage of the module (grading through the overlay), and `9031-conformance-suite-go-test`, a suite with a test that passes, one that fails an assertion, a failing subtest, one that panics, one that prints, one that ends the process, one that hangs, and a package whose test file does not compile ([Go project jobs](#go-project-jobs)).

The JVM's project fixtures: `9026-conformance-project-java` and `9027-conformance-project-kotlin`, whose entry uses a class of its own package and one of a subpackage (grading on the main runtime classpath); `9028-conformance-suite-junit-java` and `9029-conformance-suite-junit-kotlin`, suites with the six tests above, a class whose `@BeforeAll` fails (reported once, under the class's id, and left out of every restart after it), a disabled test, a failed assumption and a parameterized test (`[1]`, `[2]`).

Python's virtual-clock fixture, `9035-conformance-project-clock-python`, grades `async def` methods on the asyncio loop of `cs_support.virtual_clock`: cases with `@advance`, `@spawn`, `@join` and `@now`, four tasks that wake at the same instant (`bacd`, the order seed 0 gives), a deadlock (`stalled`, with no restart), a task left waiting (cancelled, so the case passes), a thread left running (`restart_requested`) and a `threading.Lock` taken twice (`timeout`). Its `ex1`, `advance`, `spawn-join` and `ties` cases are visible, so the generated `async def` tests of its level run as the reference's native suite, with the plugin its `pyproject.toml` loads, and every one is `ok`: seed 0 gives `ties` the same order in pytest as in grading.

TypeScript's, `9036-conformance-project-clock-typescript`, grades `Promise` methods on the mock timers: cases with `@advance`, `@spawn`, `@join` and `@now`, a chain of sleeps from the static import of `node:timers/promises` (`[10, 20, 30]`, each sleep starting when the one before it ended), sleeps that end at the same instant (`abcd`, the order they started), a deadlock (`stalled`, with no restart), a promise and a timer left pending (dropped, so the case passes) and a loop that never returns (`timeout`). Its `ex1`, `advance`, `spawn-join`, `chain` and `ties` cases are visible, so the generated tests of its level run as the reference's native suite, on the starter's copy of the helper, and every one is `ok`.

Kotlin's, `9043-conformance-project-clock-kotlin`, grades `suspend` functions on a `kotlinx-coroutines-test` scheduler through the bridge `cs.coroutines`: cases with `@advance`, `@spawn`, `@join` and `@now`, a chain of delays (`[10, 20, 30]`), coroutines that wake at the same instant (`abcd`, the order they were scheduled), a deadlock (`stalled`, with no restart), a spawned task that fails (the `error` of its `@join`), a semaphore taken twice (`timeout`) and a coroutine left active in the caller's scope (`stalled`, `the case ended with coroutines still active`, with no restart). Its `ex1`, `advance`, `spawn-join`, `chain` and `ties` cases are visible, so the generated `runTest` tests of its level run as the reference's native suite, on the scheduler of `kotlinx-coroutines-test`, and every one is `ok`.

Rust's, `9045-conformance-project-clock-rust`, grades `async fn` methods on tokio's paused clock through the runner crate's `clock` feature: cases with `@advance`, `@spawn`, `@join` and `@now`, a chain of sleeps (`[10, 20, 30]`), tasks that wake at the same instant (`abcd`, the order they were spawned), a deadlock on a notification nobody sends (`stalled`, with no restart), a spawned task that panics (the `error` of its `@join`), a parked thread (`timeout`) and a task left waiting (dropped with the case's runtime, so the case passes). Its `@spawn` cases make the bridge share the entry class, so its methods take `&self`. Its `ex1`, `advance`, `spawn-join`, `chain` and `ties` cases are visible, so the generated `#[tokio::test(start_paused = true)]` tests of its level run as the reference's native suite (`advance` as `case_advance`, since the file's helper is called `advance`), and every one is `ok`.

Go's virtual-clock fixture, `9034-conformance-project-clock-go`, is graded by its package's test binary: cases with `@advance`, `@spawn`, `@join` and `@now`, a deadlock and a goroutine left when a case ends (each `stalled` with its reason, then `restart_requested`), and a goroutine that waits on a held mutex (`timeout`); the cases after each still run. Its `advance` and `spawn-join` cases are visible, so the generated `synctest` tests of its level run as the reference's native suite and every one is `ok`.

The project stress fixtures, one per language, each a project with a stress case `s1` at level 2 and a broken overlay `unlocked-add` that loses updates: `9037-conformance-project-stress-python` (the race in a module the entry imports, which only the yields injected across the project reach), `9038-conformance-project-stress-typescript` and `9041-conformance-project-stress-go` (on the virtual clock: their sequential cases on it, their stress runs on the real clock), `9039-conformance-project-stress-java` and `9040-conformance-project-stress-kotlin` (`platform` and `virtual`), `9044-conformance-project-stress-clock-kotlin` (on the virtual clock, its methods `suspend` functions under a coroutine `Mutex`, which each worker thread calls in `runBlocking`), `9042-conformance-project-stress-rust` (a class shared through `&self`) and `9046-conformance-project-stress-clock-rust` (the same on the virtual clock, its `add` an `async fn` that each worker thread blocks on, on a runtime of its own on the real clock). The reference passes `s1` in 10 of 10 runs per variant; the broken overlay, run as approach `broken-unlocked-add`, passes the sequential cases and fails `s1` in at least 9 of 10.

Rust's project fixtures: `9032-conformance-project-rust`, a crate whose entry module uses a sibling by `crate::` and by `super::` path and is re-exported at the crate root (grading); `9033-conformance-suite-cargo`, a suite with a test that passes, one that fails an assertion, one that panics, one that hangs, one that aborts, one that prints, an ignored test, a `should_panic` test, and a test file that does not compile (one process per test: the hang and the abort end only their own test).

Fixtures live in `runners/conformance/<id>-<slug>/`; each language adds its reference files as `solutions/<approach>.<ext>`. `runners/conformance/expectations.json` (schema `schemas/conformance.schema.json`) gives the expected outcome per fixture and approach (`pass`, `error`, `invalid_output`, `timeout`, `load_error`) with per-case overrides, and `runners/conformance/README.md` states what every approach does in each language.
