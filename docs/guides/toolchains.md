# Install the language toolchains

`cstudy` builds and runs your solutions with the real toolchains of each language, and you install those yourself: neither Homebrew nor uv pulls them in with `cstudy`. This guide gives the recommended install on macOS and Linux and the command that checks it. `cstudy doctor` runs the same checks and links back here when one fails.

| Toolchain | Version `cstudy doctor` accepts | Needed for |
|-----------|---------------------------------|------------|
| [uv and Python](#python-and-uv) | uv (any version; 0.10 or newer recommended), Python 3.13 found by `uv python find 3.13` | Required: `cstudy` and the Python practice project |
| [Node.js and pnpm](#nodejs-and-pnpm) | Node 24 or newer, any pnpm (9 or newer recommended) | TypeScript |
| [JDK](#jdk) | 21 to 26 (25 recommended); 27 and newer are not supported yet | Java and Kotlin |
| [Go](#go) | Go 1.25 or newer; Delve (`dlv`, any version, 1.27.2 tested) for `--debug` | Optional: `--lang go` |
| [Rust](#rust) | `rustc` 1.80 or newer and `cargo`, through rustup; LLDB's `debugserver` (macOS) or `lldb-server` (Linux) for `--debug` | Optional: `--lang rust` |
| [git](#git) | Any | Optional: versioning your workspace |

You need only the toolchains of the languages you practice. `cstudy doctor` still reports a missing one as `FAIL`, and exits 4, when you do not use that language, except Go and Rust: problems have Go and Rust references, but their toolchains are optional, so a missing or too old one is a `WARN` ("needed for `--lang go`") and the exit code stays 0. Their debuggers, Delve and Rust's debug server, are `WARN`s too: only `cstudy test --debug` needs them.

On Linux, the installs below were checked on Ubuntu 24.04 (arm64), where the system packages they need are:

```bash
sudo apt install build-essential git lldb openjdk-21-jdk
```

`build-essential` provides the C linker that Rust needs, and `lldb` provides `lldb-server` for `--debug` with Rust. uv, Node, Go and Rust come from their own installers, as each section shows.

## Python and uv

uv installs Python 3.13 and manages the workspace's Python project (`python/`), whose virtual environment `cstudy doctor --fix` creates with `uv sync`. Install uv with its standalone installer on either system, or with Homebrew on macOS:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # macOS and Linux
brew install uv                                  # macOS, alternative
```

`cstudy doctor` looks for Python 3.13 with `uv python find 3.13`, which also finds interpreters on `PATH`, such as the `python@3.13` that the Homebrew formula installs. When it finds none, install one through uv:

```bash
uv python install 3.13
```

Check both:

```bash
uv --version            # uv 0.10.0 or newer
uv python find 3.13     # prints the path of a Python 3.13 interpreter
```

The workspace's Python project also lists `debugpy`, which only `cstudy test --debug` needs; `cstudy doctor --fix` installs it with the rest of the project.

## Node.js and pnpm

The TypeScript runner runs your `.ts` files directly with Node's type stripping, which needs Node 24 or newer. pnpm installs the workspace's TypeScript project (`typescript/`). We recommend [fnm](https://github.com/Schniz/fnm) to install Node, and Corepack, which ships with Node 24, to provide pnpm.

1. Install fnm:

   ```bash
   brew install fnm                                  # macOS
   curl -fsSL https://fnm.vercel.app/install | bash  # Linux
   ```

2. Load fnm in your shell, by adding this line to `~/.zshrc` (for bash, use `--shell bash` in `~/.bashrc`), then open a new terminal:

   ```bash
   eval "$(fnm env --use-on-cd --shell zsh)"
   ```

3. Install Node 24 and make it the default:

   ```bash
   fnm install 24
   fnm default 24
   ```

4. Enable pnpm through Corepack. If the `corepack` command is not found, run `npm install --global corepack` first.

   ```bash
   corepack enable pnpm
   ```

Check both:

```bash
node --version   # v24.0.0 or newer
pnpm --version   # 9.0.0 or newer
```

nvm (`nvm install 24`) works as well as fnm, and on macOS `brew install node pnpm` installs both without a version manager.

## JDK

`cstudy` builds and runs Java and Kotlin with the JDK your shell selects: the one `JAVA_HOME` names, else the one of the first `java` on `PATH`, as the Gradle wrapper does. It supports JDK 21 to 26. `cstudy doctor` passes any of them, fails JDK 20 and older, and reports JDK 27 and newer as not supported yet: the Kotlin compiler that `cstudy` pins targets JDK 26 at most. The vendor does not matter. We recommend JDK 25, the newest long-term-support release in the range, installed with [SDKMAN!](https://sdkman.io) on macOS and Linux.

1. Install SDKMAN, then open a new terminal:

   ```bash
   curl -s "https://get.sdkman.io" | bash
   ```

2. List the Java builds and pick a Temurin 25 identifier, the line ending in `-tem` whose version starts with `25.`:

   ```bash
   sdk list java
   ```

3. Install it and make it the default `java`. The identifier below was current on November 1, 2026; use the one from your list. A plain `sdk install java` installs SDKMAN's current default, which can be a release above 26.

   ```bash
   sdk install java 25.0.5.0+8-tem
   sdk default java 25.0.5.0+8-tem
   ```

Check it:

```bash
java -version   # openjdk version "25.0.5" ...
cstudy doctor   # ok    java 25.0.5 (JAVA_HOME)
```

On macOS, Homebrew works too, with the versioned formula: `brew install openjdk` installs JDK 27, which `cstudy` does not support yet.

```bash
brew install openjdk@25
export JAVA_HOME="$(brew --prefix openjdk@25)/libexec/openjdk.jdk/Contents/Home"   # add to your shell profile
```

On Linux, your distribution's packages work too: on Debian and Ubuntu, `sudo apt install openjdk-21-jdk`, or `openjdk-25-jdk` where your release has it; on Fedora, `sudo dnf install java-21-openjdk-devel` or `java-25-openjdk-devel`.

Several JDKs can be installed side by side. `cstudy` never looks for them: it uses the one your shell selects, so `sdk use java <identifier>` in one terminal, or a `.sdkmanrc` in a directory, switches it. Switching starts another Gradle daemon and compiles once more. Your Java and Kotlin code compiles at the level of the selected JDK, up to 26, so a newer JDK lets you use its language features and APIs. A problem that needs a newer JDK than 21 says so in its statement, and `cstudy` refuses to start it on an older one.

One known gap is JDK 22. With the JDK 22.0.0 build we test, the Kotlin compiler cannot read that JDK's API signatures when it compiles a problem's reference solution at JDK 21's level. So `cstudy bench` and `cstudy verify` fail for Kotlin problems, while your own Kotlin code and every Java command work. JDK 22 no longer receives updates, so select JDK 25 instead.

Nothing else is needed for Java or Kotlin:

- **Gradle**: each workspace ships the Gradle wrapper (`jvm/gradlew`), which downloads its own Gradle on first use. `cstudy doctor` reports a missing system Gradle as `WARN`; only a maintainer who regenerates the wrapper needs one (`brew install gradle`, or `sdk install gradle` on Linux, although the warning names Homebrew).
- **Kotlin**: the Kotlin Gradle plugin compiles the Kotlin project, and Gradle downloads it with the build, so `kotlinc` is not required. Install it with `sdk install kotlin` only if you want a Kotlin REPL.
- **kotlinx-coroutines**: a Kotlin project problem on the virtual clock builds with `kotlinx-coroutines-core` and `kotlinx-coroutines-test` (1.11.0), which `cstudy doctor --fix` caches with JUnit, online once. A workspace set up before them gets them from its next `cstudy doctor --fix`; until then `cstudy doctor` warns on `kotlin project libraries`.

## Go

The Go toolchain is optional: only `--lang go` builds with it, and `cstudy doctor` warns, without failing, when it is missing. The workspace's Go project (`go/`) is a module that needs Go 1.25 or newer: Go 1.24 introduced the `go build -json` output that `cstudy` parses, and Go 1.25 added `testing/synctest.Test`, which grades the projects that wait on a virtual clock ([ADR 0017](../decisions/0017-async-project-problems.md)). Go 1.24 is past its upstream support. A workspace on Go 1.24 upgrades before its next Go run, and a `go.mod` that says `go 1.24` keeps building. The standard installers all work: Homebrew on macOS, or the installer or archive from [go.dev/dl](https://go.dev/dl/) on macOS and Linux (follow [go.dev/doc/install](https://go.dev/doc/install) for the archive).

```bash
brew install go   # macOS
```

On Linux, prefer the go.dev archive: the Go package of a distribution is often older than 1.25.

Check it:

```bash
go version   # go version go1.25.0 or newer
```

Nothing else is needed: the runner uses the standard library, and the one module a solution may import, `github.com/shopspring/decimal` for `decimal`, ships with `cstudy` and is reached through a `replace` in `go/go.mod`. So `cstudy` never downloads a module, gopls finds the package offline, and `cstudy doctor --fix` has no Go step.

- **`GOTOOLCHAIN=local`**: since Go 1.21 the `go` command downloads the toolchain a `go.mod` asks for, and `go/go.mod` says `go 1.24`. `cstudy` builds with `GOTOOLCHAIN=local` and never downloads one, so with an older Go it stops with an error instead. Export `GOTOOLCHAIN=local` in your shell as well if you want your own `go` commands, and your editor, to behave the same way.
- **Your Go settings**: `cstudy` pins its own build environment (`GOENV=off`, `GOFLAGS=-mod=readonly`, `GOPROXY=off`, and your `GOOS`, `GOARCH` and `GOWORK` removed), so `go env -w` values and shell variables never change how it builds. They still apply to the `go` commands you run yourself. The Go build cache is kept, so the standard library compiles once per machine.
- **Editor**: the `go.work` file at the workspace root lets gopls find the module in `go/`, so open the workspace root. The workspace's VS Code files recommend the Go extension (`golang.go`) and run its tools with `GOTOOLCHAIN=local`; `cstudy ide` adds them to a workspace created earlier.
- **Debugging**: `cstudy test --debug` runs the Go runner under [Delve](https://github.com/go-delve/delve). Install the release `cstudy` is tested with, `go install github.com/go-delve/delve/cmd/dlv@v1.27.2`, and check it with `dlv version`. `go install` puts `dlv` in `GOBIN`, or in `bin` of your `GOPATH` (`~/go/bin`), where `cstudy` finds it even when that directory is not on `PATH`. Delve 1.27.2 debugs only programs built with Go 1.25 or newer, and refuses older ones (`Go version go1.24.x is too old for this version of Delve`), so debugging Go needs Go 1.25 or newer, the same minimum as building; on an older Go `cstudy test --debug` exits 4 and shows Delve's message, for a single file and for a project. On macOS Delve runs your code through Xcode's `debugserver`, so it needs the Command Line Tools and the permission to debug described under [Rust](#rust). In VS Code, **Debug current file (Go)** starts the run and attaches the Go extension. `cstudy doctor` warns while `dlv` is missing, and while your Go is older than the Go that your Delve debugs (the `dlv` row then names the Go to install).

## Rust

The Rust toolchain is optional: only `--lang rust` builds with it, and `cstudy doctor` warns, without failing, when `rustc` or `cargo` is missing or `rustc` is older than 1.80. Install it with [rustup](https://rustup.rs), which manages toolchains and components. Do not use Homebrew's `rust` formula: it has no `rust-src` and no toolchain management, so rust-analyzer cannot show the standard library and you cannot pick a version.

```bash
brew install rustup   # macOS
rustup-init           # installs the stable toolchain and puts cargo on PATH
```

or, on macOS and Linux, the script from rustup.rs:

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

On Linux, Rust links with the system's C toolchain: install `build-essential` on Debian and Ubuntu first. Open a new terminal afterwards, so `~/.cargo/bin` is on `PATH`. For rust-analyzer in your editor, add the standard library sources:

```bash
rustup component add rust-src
```

Check it:

```bash
rustc --version   # rustc 1.80.0 or newer
cargo --version
```

Nothing else is needed: the runner crates' only dependencies, `rust_decimal` and `chrono` for `decimal` and `date`, and tokio 1.53.3 for the Rust projects that wait on a virtual clock, ship with `cstudy` as vendored crates, so builds run with `cargo --offline`, never contact crates.io, and `cstudy doctor --fix` has no Rust step. tokio 1.53 is the newest release that builds with Rust 1.80; a workspace set up before it gets it with the runner runtime that the next `cstudy` command refreshes.

- **Your Cargo setup**: `cstudy` ignores your Cargo configuration for its builds. `RUSTFLAGS`, rustc wrappers such as `sccache`, `CARGO_TARGET_DIR`, `CARGO_BUILD_*` and `CARGO_PROFILE_*` do not reach them, and crates.io always resolves to the vendored crates, so none can break a build or change what it measures. They still apply to the `cargo` commands you run yourself. Builds go to `.cs/build/rust` in the workspace.
- **Copied files**: Cargo rebuilds a crate only when a source is newer than the last build, so a file replaced by a copy that keeps an older time (`rsync -a`, `cp -p`) would run the old code. `cstudy` records a digest of your practice file, or of the Rust files and `Cargo.toml` of a project folder, at each build, and touches the ones that changed before Cargo runs, so the new code always builds. Nothing else is needed; your own `cargo` commands in `rust/` do not get this and still go by times.
- **Editor**: `rust/Cargo.toml` lists each problem you start, so rust-analyzer checks every file; open the workspace root, or `rust/`. Its `rust/.cargo/config.toml` resolves `rust_decimal` and `chrono` from the vendored crates, for `cargo` commands run in `rust/`. The workspace's VS Code files recommend rust-analyzer (`rust-lang.rust-analyzer`), link `rust/Cargo.toml` and check every target; `cstudy ide` adds them to a workspace created earlier. If an older `cstudy` wrote `"rust-analyzer.check.extraArgs": ["--keep-going"]` into your `.vscode/settings.json` and you edited that file, remove the key (rust-analyzer already passes `--keep-going`, and cargo rejects it twice), or run `cstudy ide --force`. The extension's rust-analyzer needs a recent stable toolchain: with an older one it reports an outdated toolchain and may flag standard macros such as `todo!` and `vec!`, which `rustup update` fixes.
- **Debugging**: `cstudy test --debug` runs the Rust runner under LLDB's debug server, and in VS Code **Debug current file (Rust)** attaches CodeLLDB (`vadimcn.vscode-lldb`, which the workspace's VS Code files recommend). On macOS the server is `debugserver`, which the Xcode Command Line Tools (`xcode-select --install`) and Xcode ship inside LLDB.framework; `cstudy` finds it as `lldb` does, through `xcode-select -p`. macOS lets a program be debugged only with permission: members of the `_developer` group have it (`id -Gn` lists your groups); for anyone else macOS asks for an administrator when a debug session starts, until an administrator turns developer mode on with `sudo DevToolsSecurity -enable`. On Linux the server is `lldb-server`, from your distribution's `lldb` package (`sudo apt install lldb` on Debian and Ubuntu; a versioned package alone, such as `lldb-18`, installs only `lldb-server-18`), and `cstudy` looks for it on `PATH`. In a Docker container, start the container with `--security-opt seccomp=unconfined`: the default profile refuses the call `lldb-server` makes to turn off address randomization, and the debug run stops with `personality set failed: Operation not permitted`. A debugged test of a Rust project problem is reported as an `error` on Linux, because `lldb-server` sends the test's output only to your debugger: read the result there. `cstudy doctor` warns while the server is missing.

## git

git is optional: `cstudy init --git` runs `git init` in the new workspace, and `cstudy` never commits. macOS provides git with the Xcode Command Line Tools (`xcode-select --install`) or `brew install git`; on Linux, install your distribution's `git` package.

## Your environment

`cstudy` runs your code, its tests and the tools beside them (the builds, `uv sync`, `pnpm install`, the language servers of the web page) with part of your shell's environment, not all of it. A token, key or password you exported (`GITHUB_TOKEN`, `AWS_SECRET_ACCESS_KEY`, `OPENAI_API_KEY` and the like) does not reach them, so a solution or a dependency cannot read it from the environment. It can still read your files, so keep credentials out of the workspace: `cstudy` runs your code as you and has no sandbox.

What passes is what the toolchains need to find themselves and the network: `PATH`, `HOME`, your locale, terminal and temporary-directory variables, `JAVA_HOME` and `SDKMAN_*`, `GRADLE_USER_HOME` and `GRADLE_OPTS`, `GOPATH`, `GOCACHE`, `GOMODCACHE` and `GOROOT`, `CARGO_HOME` and `RUSTUP_*`, `VIRTUAL_ENV`, `NODE_OPTIONS`, `PNPM_HOME`, uv's cache, interpreter and offline settings, and your proxy and CA-certificate variables (`HTTPS_PROXY`, `NO_PROXY`, `SSL_CERT_FILE`, `NODE_EXTRA_CA_CERTS` and the like), so `cstudy doctor --fix` keeps working behind a corporate network. A proxy URL passes as you wrote it, credentials included. The full list is in the [runners spec](../specs/runners.md#process-environment).

Two things to expect. A variable you set only for your own commands, such as `PYTHONPATH`, `NODE_ENV` or `RUST_BACKTRACE`, does not reach the ones `cstudy` runs, and neither do a private registry's credentials, so an install that needs one fails with the tool's own message; run that install yourself in the project folder. Tools that a version manager (pyenv, asdf, mise) selects are found through `PATH`, so keep its shims or the selected version's directory there.

## Check everything

Run `cstudy doctor` to check the toolchains. In a workspace, `cstudy doctor --fix` then sets up each project: `uv sync` in `python/`, `pnpm install` in `typescript/`, and a first Gradle build in `jvm/`. It also writes the template files a workspace from an older `cstudy` lacks, such as the `go/` and `rust/` projects, which `cstudy doctor` reports as a `WARN` until then. Go and Rust need no setup command.

```bash
cstudy doctor
cd ~/cstudy-workspace && cstudy doctor --fix
```

[cstudy doctor](../specs/cli.md#cstudy-doctor) lists every check and its fix.
