# Install the language toolchains

`cstudy` builds and runs your solutions with the real toolchains of each language, and you install those yourself: neither Homebrew nor uv pulls them in with `cstudy`. This guide gives the recommended install on macOS and Linux and the command that checks it. `cstudy doctor` runs the same checks and links back here when one fails.

| Toolchain | Version `cstudy doctor` accepts | Needed for |
|-----------|---------------------------------|------------|
| [uv and Python](#python-and-uv) | uv (any version; 0.10 or newer recommended), Python 3.13 found by `uv python find 3.13` | Required: `cstudy` and the Python practice project |
| [Node.js and pnpm](#nodejs-and-pnpm) | Node 24 or newer, any pnpm (9 or newer recommended) | TypeScript |
| [JDK 21](#jdk-21) | Exactly major version 21 | Java and Kotlin |
| [Go](#go) | Go 1.24 or newer; Delve (`dlv`, any version, 1.27.2 tested) for `--debug` | Optional: `--lang go` |
| [Rust](#rust) | `rustc` 1.80 or newer and `cargo`, through rustup; LLDB's `debugserver` (macOS) or `lldb-server` (Linux) for `--debug` | Optional: `--lang rust` |
| [git](#git) | Any | Optional: versioning your workspace |

You need only the toolchains of the languages you practice. `cstudy doctor` still reports a missing one as `FAIL`, and exits 4, when you do not use that language, except Go and Rust: they are optional languages, so a missing or too old one is a `WARN` ("needed for `--lang go`") and the exit code stays 0. Their debuggers, Delve and Rust's debug server, are `WARN`s too: only `cstudy test --debug` needs them.

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

## JDK 21

The Java and Kotlin practice projects build with Gradle against a Java 21 toolchain, and `cstudy doctor` requires `java -version` to report major version 21: JDK 17 and JDK 25 both fail. The vendor does not matter. We recommend [SDKMAN!](https://sdkman.io) on macOS and Linux, with Eclipse Temurin.

1. Install SDKMAN, then open a new terminal:

   ```bash
   curl -s "https://get.sdkman.io" | bash
   ```

2. List the Java builds and pick a Temurin 21 identifier, the line ending in `-tem` whose version starts with `21.`:

   ```bash
   sdk list java
   ```

3. Install it and make it the default `java`. The identifier below was current on October 29, 2026; use the one from your list. A plain `sdk install java` installs the newest release (25 or later), which `cstudy doctor` rejects.

   ```bash
   sdk install java 21.0.13.0+9-tem
   sdk default java 21.0.13.0+9-tem
   ```

Check it:

```bash
java -version   # openjdk version "21.0.13" ...
```

Nothing else is needed for Java or Kotlin:

- **Gradle**: each workspace ships the Gradle wrapper (`jvm/gradlew`), which downloads its own Gradle on first use. `cstudy doctor` reports a missing system Gradle as `WARN`; only a maintainer who regenerates the wrapper needs one (`brew install gradle`).
- **Kotlin**: the Kotlin Gradle plugin compiles the Kotlin project, and Gradle downloads it with the build, so `kotlinc` is not required. Install it with `sdk install kotlin` only if you want a Kotlin REPL.

Alternatives to SDKMAN: on macOS, `brew install openjdk@21`, then follow its caveats to put it on `PATH`; on Debian and Ubuntu, `sudo apt install openjdk-21-jdk`; on Fedora, `sudo dnf install java-21-openjdk-devel`.

## Go

Go is optional: only `--lang go` builds with it, and `cstudy doctor` warns, without failing, when it is missing. The workspace's Go project (`go/`) is a module that needs Go 1.24 or newer, the first release whose `go build -json` output `cstudy` parses. The standard installers all work: Homebrew on macOS, or the installer or archive from [go.dev/dl](https://go.dev/dl/) on macOS and Linux (follow [go.dev/doc/install](https://go.dev/doc/install) for the archive).

```bash
brew install go   # macOS
```

On Linux, prefer the go.dev archive: the Go package of a distribution is often older than 1.24.

Check it:

```bash
go version   # go version go1.24.0 or newer
```

Nothing else is needed: the runner uses the standard library, and the one module a solution may import, `github.com/shopspring/decimal` for `decimal`, ships with `cstudy` and is reached through a `replace` in `go/go.mod`. So `cstudy` never downloads a module, gopls finds the package offline, and `cstudy doctor --fix` has no Go step.

- **`GOTOOLCHAIN=local`**: since Go 1.21 the `go` command downloads the toolchain a `go.mod` asks for, and `go/go.mod` says `go 1.24`. `cstudy` builds with `GOTOOLCHAIN=local` and never downloads one, so with an older Go it stops with an error instead. Export `GOTOOLCHAIN=local` in your shell as well if you want your own `go` commands, and your editor, to behave the same way.
- **Your Go settings**: `cstudy` pins its own build environment (`GOENV=off`, `GOFLAGS=-mod=readonly`, `GOPROXY=off`, and your `GOOS`, `GOARCH` and `GOWORK` removed), so `go env -w` values and shell variables never change how it builds. They still apply to the `go` commands you run yourself. The Go build cache is kept, so the standard library compiles once per machine.
- **Editor**: the `go.work` file at the workspace root lets gopls find the module in `go/`, so open the workspace root. The workspace's VS Code files recommend the Go extension (`golang.go`) and run its tools with `GOTOOLCHAIN=local`; `cstudy ide` adds them to a workspace created earlier.
- **Debugging**: `cstudy test --debug` runs the Go runner under [Delve](https://github.com/go-delve/delve). Install the release `cstudy` is tested with, `go install github.com/go-delve/delve/cmd/dlv@v1.27.2`, and check it with `dlv version`. `go install` puts `dlv` in `GOBIN`, or in `bin` of your `GOPATH` (`~/go/bin`), where `cstudy` finds it even when that directory is not on `PATH`. On macOS Delve runs your code through Xcode's `debugserver`, so it needs the Command Line Tools and the permission to debug described under [Rust](#rust). In VS Code, **Debug current file (Go)** starts the run and attaches the Go extension. `cstudy doctor` warns while `dlv` is missing.

## Rust

Rust is optional: only `--lang rust` builds with it, and `cstudy doctor` warns, without failing, when `rustc` or `cargo` is missing or `rustc` is older than 1.80. Install it with [rustup](https://rustup.rs), which manages toolchains and components. Do not use Homebrew's `rust` formula: it has no `rust-src` and no toolchain management, so rust-analyzer cannot show the standard library and you cannot pick a version.

```bash
brew install rustup   # macOS
rustup-init           # installs the stable toolchain and puts cargo on PATH
```

or, on macOS and Linux, the script from rustup.rs:

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

Open a new terminal afterwards, so `~/.cargo/bin` is on `PATH`. For rust-analyzer in your editor, add the standard library sources:

```bash
rustup component add rust-src
```

Check it:

```bash
rustc --version   # rustc 1.80.0 or newer
cargo --version
```

Nothing else is needed: the runner crates' only dependencies, `rust_decimal` and `chrono` for `decimal` and `date`, ship with `cstudy` as vendored crates, so builds run with `cargo --offline`, never contact crates.io, and `cstudy doctor --fix` has no Rust step.

- **Your Cargo setup**: `cstudy` ignores your Cargo configuration for its builds. `RUSTFLAGS`, rustc wrappers such as `sccache`, `CARGO_TARGET_DIR`, `CARGO_BUILD_*` and `CARGO_PROFILE_*` do not reach them, and crates.io always resolves to the vendored crates, so none can break a build or change what it measures. They still apply to the `cargo` commands you run yourself. Builds go to `.cs/build/rust` in the workspace.
- **Editor**: `rust/Cargo.toml` lists each problem you start, so rust-analyzer checks every file; open the workspace root, or `rust/`. Its `rust/.cargo/config.toml` resolves `rust_decimal` and `chrono` from the vendored crates, for `cargo` commands run in `rust/`. The workspace's VS Code files recommend rust-analyzer (`rust-lang.rust-analyzer`), link `rust/Cargo.toml` and check with `--keep-going`; `cstudy ide` adds them to a workspace created earlier. The extension's rust-analyzer needs a recent stable toolchain: with an older one it reports an outdated toolchain and may flag standard macros such as `todo!` and `vec!`, which `rustup update` fixes.
- **Debugging**: `cstudy test --debug` runs the Rust runner under LLDB's debug server, and in VS Code **Debug current file (Rust)** attaches CodeLLDB (`vadimcn.vscode-lldb`, which the workspace's VS Code files recommend). On macOS the server is `debugserver`, which the Xcode Command Line Tools (`xcode-select --install`) and Xcode ship inside LLDB.framework; `cstudy` finds it as `lldb` does, through `xcode-select -p`. macOS lets a program be debugged only with permission: members of the `_developer` group have it (`id -Gn` lists your groups); for anyone else macOS asks for an administrator when a debug session starts, until an administrator turns developer mode on with `sudo DevToolsSecurity -enable`. On Linux the server is `lldb-server`, from your distribution's `lldb` package; `cstudy` looks for it on `PATH` (not tried on Linux yet). `cstudy doctor` warns while the server is missing.

## git

git is optional: `cstudy init --git` runs `git init` in the new workspace, and `cstudy` never commits. macOS provides git with the Xcode Command Line Tools (`xcode-select --install`) or `brew install git`; on Linux, install your distribution's `git` package.

## Check everything

Run `cstudy doctor` to check the toolchains. In a workspace, `cstudy doctor --fix` then sets up each project: `uv sync` in `python/`, `pnpm install` in `typescript/`, and a first Gradle build in `jvm/`. It also writes the template files a workspace from an older `cstudy` lacks, such as the `go/` and `rust/` projects, which `cstudy doctor` reports as a `WARN` until then. Go and Rust need no setup command.

```bash
cstudy doctor
cd ~/cstudy-workspace && cstudy doctor --fix
```

[cstudy doctor](../specs/cli.md#cstudy-doctor) lists every check and its fix.
