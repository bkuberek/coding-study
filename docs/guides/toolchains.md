# Install the language toolchains

`cstudy` builds and runs your solutions with the real toolchains of each language, and you install those yourself: neither Homebrew nor uv pulls them in with `cstudy`. This guide gives the recommended install on macOS and Linux and the command that checks it. `cstudy doctor` runs the same checks and links back here when one fails.

| Toolchain | Version `cstudy doctor` accepts | Needed for |
|-----------|---------------------------------|------------|
| [uv and Python](#python-and-uv) | uv (any version; 0.10 or newer recommended), Python 3.13 found by `uv python find 3.13` | Required: `cstudy` and the Python practice project |
| [Node.js and pnpm](#nodejs-and-pnpm) | Node 24 or newer, any pnpm (9 or newer recommended) | TypeScript |
| [JDK 21](#jdk-21) | Exactly major version 21 | Java and Kotlin |
| [git](#git) | Any | Optional: versioning your workspace |

You need only the toolchains of the languages you practice. `cstudy doctor` still reports a missing one as `FAIL`, and exits 4, when you do not use that language.

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

## git

git is optional: `cstudy init --git` runs `git init` in the new workspace, and `cstudy` never commits. macOS provides git with the Xcode Command Line Tools (`xcode-select --install`) or `brew install git`; on Linux, install your distribution's `git` package.

## Check everything

Run `cstudy doctor` to check the toolchains. In a workspace, `cstudy doctor --fix` then sets up each project: `uv sync` in `python/`, `pnpm install` in `typescript/`, and a first Gradle build in `jvm/`.

```bash
cstudy doctor
cd ~/cstudy-workspace && cstudy doctor --fix
```

[cstudy doctor](../specs/cli.md#cstudy-doctor) lists every check and its fix.
