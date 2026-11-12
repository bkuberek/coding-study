# Review: the facts of the getting-started guides

The nine guides of the path "Getting started: from the terminal to your first problem" ([guides](../specs/guides.md), [ADR 0025](../decisions/0025-concept-guides-and-learning-paths.md)) state facts about shells, package managers, six languages and cstudy itself. This page lists each one with where it was checked, so that a later review starts from the sources, and records what the independent accuracy review changes.

"Quote" means the exact text was read on that page. "Run" means an example of the guide, or a one-off command, printed it: on GNU bash 5.2.21, zsh 5.9, CPython 3.13.12, Node 24.21.0 and OpenJDK 21.0.2 on Ubuntu, with cstudy 0.41.0 from this branch in a scratch workspace. "Repo" means it was read in this repository: cstudy's own specs, guides, code or problems. A fact that could not be checked was left out of the guides; the last section lists them.

## Shells and the terminal

| # | Claim | Source |
|---|-------|--------|
| T1 | A Unix shell is "both a command interpreter and a programming language" | Quote: [Bash manual, What is a shell?](https://www.gnu.org/software/bash/manual/html_node/What-is-a-shell_003f.html) |
| T2 | Starting with macOS 10.15, zsh is the default login and interactive shell; bash was the default in 10.14 and earlier; `chsh -s` with a path from `/etc/shells`; starting bash shows a message that the default interactive shell is now zsh | Quote: [Apple, Use zsh as the default shell on Mac](https://support.apple.com/en-us/102360) |
| T3 | macOS Catalina 10.15 was released on 7 October 2019 | Quote: [About the security content of macOS Catalina 10.15](https://support.apple.com/en-us/103107) ("Released October 7, 2019"); [Apple Newsroom, 7 October 2019](https://www.apple.com/newsroom/2019/10/macos-catalina-is-available-today/) |
| T4 | Terminal is in `/Applications/Utilities` | Quote: [Open or quit Terminal on Mac](https://support.apple.com/guide/terminal/open-or-quit-terminal-apd5265185d-f365-44cb-8b09-71a064a42125/mac) |
| T5 | Terminal's settings choose the shell it opens ("Shells open with") | Quote: [Change the default shell in Terminal](https://support.apple.com/guide/terminal/change-the-default-shell-trml113/mac) |
| T6 | Windows Terminal hosts Command Prompt, PowerShell and bash through WSL | Quote: [Windows Terminal overview](https://learn.microsoft.com/en-us/windows/terminal/) |
| T7 | bash runs a function, then a builtin, then searches `PATH`, remembering found paths in a hash table; a failed search prints an error and returns 127 | Quote: [Bash manual, Command Search and Execution](https://www.gnu.org/software/bash/manual/html_node/Command-Search-and-Execution.html) |
| T8 | `PATH` is "a colon-separated list of directories in which the shell looks for commands"; `HOME` is the default for `cd`; `SHELL` expands to the full pathname of the shell | Quote: [Bash Reference Manual](https://tiswww.case.edu/php/chet/bash/bashref.html) §5.1, §5.2 |
| T9 | zsh runs a function, then a builtin, then searches `$path`; the error is `command not found: cmd`, status 127 | Quote: [zsh manual, Command Execution](https://zsh.sourceforge.io/Doc/Release/Command-Execution.html) |
| T10 | zsh's `path` array holds the directories, and `PATH` is the same elements joined by colons | Quote: [zsh manual, Parameters](https://zsh.sourceforge.io/Doc/Release/Parameters.html) |
| T11 | zsh's `HASH_CMDS` is on by default and saves each command's location, avoiding a path search | Quote: [zsh manual, Options](https://zsh.sourceforge.io/Doc/Release/Options.html) |
| T12 | `hash -r` forgets every remembered location in bash; zsh's `rehash` is `hash -r` | Quote: Bash Reference Manual §4.1; [zsh manual, Shell Builtin Commands](https://zsh.sourceforge.io/Doc/Release/Shell-Builtin-Commands.html) |
| T13 | bash's `type` tells how a name would be interpreted; zsh's `type` is `whence -v` and its `which` is `whence -c`, a builtin; in bash, `which` is the program `/usr/bin/which` | Quote: Bash Reference Manual §4.2; zsh Shell Builtin Commands. Run: `type which` in bash and zsh |
| T14 | `command -v` is POSIX and prints the path or command the shell would use; for `cd` it prints `cd`, and `type cd` prints `cd is a shell builtin` | Quote: [POSIX `command`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/command.html). Run: bash and zsh |
| T15 | Interactive messages `bash: pyhton3: command not found` and `zsh: command not found: pyhton3`, status 127 | Run: interactive bash and zsh |
| T16 | `cd` with no argument goes to `HOME`; `cd -` goes to `$OLDPWD`; `pwd` prints the absolute pathname of the current directory | Quote: Bash Reference Manual §4.1. Run: `cd -` in zsh |
| T17 | `~` expands to the value of `HOME` | Quote: Bash Reference Manual §3.5.2 |
| T18 | A simple command is words separated by blanks; quoting removes the special meaning of characters | Quote: Bash Reference Manual §3.1.2, §3.2.2 |
| T19 | Assignment is `name=[value]`; `export` marks names to be passed to commands executed afterwards, in bash and in zsh | Quote: Bash Reference Manual §3.4, §4.1; zsh Shell Builtin Commands |
| T20 | Executed commands receive the environment; a command in its separate environment cannot affect the shell's | Quote: Bash Reference Manual §3.7.3, §3.7.4. Run: `environment.py` |
| T21 | Exit status 0 is success and non-zero failure; 127 not found, 126 found but not executable; `$?` holds the last one | Quote: Bash Reference Manual §3.7.5 |
| T22 | `>` creates or truncates the file; `>>` appends; `2>` redirects standard error | Quote: Bash Reference Manual §3.6 |
| T23 | A pipe connects each command's output to the next one's input; each command of a multi-command pipeline runs in its own subshell, a separate process; the pipeline's status is the last command's unless `pipefail` is set | Quote: Bash Reference Manual §3.2.3 |
| T24 | bash login shells read `/etc/profile`, then the first of `~/.bash_profile`, `~/.bash_login` and `~/.profile`; interactive non-login shells read `~/.bashrc`; the suggested line `if [ -f ~/.bashrc ]; then . ~/.bashrc; fi` | Quote: Bash Reference Manual §6.2 |
| T25 | zsh reads `.zshenv` always, `.zprofile` for login shells, `.zshrc` for interactive shells, then `.zlogin` for login shells; `ZDOTDIR` defaults to `HOME` | Quote: [zsh manual, Files](https://zsh.sourceforge.io/Doc/Release/Files.html) |
| T26 | `.` and `source` read and execute a file in the current shell | Quote: Bash Reference Manual §4.1, §4.2; zsh Shell Builtin Commands |
| T27 | POSIX `ls -a` lists names starting with a period, `ls -l` the long format; `head` and `tail` default to 10 lines; `cat`, `sort -r`, `mkdir` | Quote: POSIX Issue 8 [`ls`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ls.html), [`head`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/head.html), [`tail`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/tail.html), [`cat`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/cat.html), [`sort`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sort.html), [`mkdir`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/mkdir.html) |
| T28 | `less` is a pager: Space scrolls a window forward, `q` quits, `h` shows help | Quote: [less(1)](https://man7.org/linux/man-pages/man1/less.1.html); [less home page](https://www.greenwoodsoftware.com/less/) |
| T29 | A Python traceback starts with `Traceback (most recent call last):`, and "The last line of the error message indicates what happened"; the `ZeroDivisionError` example | Quote: [Python tutorial, Errors and Exceptions](https://docs.python.org/3/tutorial/errors.html) |
| T30 | An uncaught Python exception ends the program with status 1 and writes the traceback to standard error | Run: `environment.py` |
| T31 | GNU `ls` on a missing name prints `ls: cannot access 'no-such-folder': No such file or directory` and exits 2 | Run: Ubuntu's `ls` |
| T32 | VS Code's integrated terminal starts at the workspace root with the system's default shell | Quote: [VS Code, terminal basics](https://code.visualstudio.com/docs/terminal/basics) |
| T33 | Oh My Zsh is "an open source, community-driven framework for managing your zsh configuration"; it renames `~/.zshrc` to `~/.zshrc.pre-oh-my-zsh`; `plugins=(...)` and `ZSH_THEME` in `~/.zshrc`; `uninstall_oh_my_zsh`; inspect an install script from a project you do not know | Quote: [Oh My Zsh README](https://github.com/ohmyzsh/ohmyzsh); [ohmyz.sh](https://ohmyz.sh/) |
| T34 | The worked session: `>` replacing the three lines with `kiwi`, `>>` adding lines, `sort fruit.txt \| head -n 2` printing `apple` and `banana` | Run: zsh 5.9, with the home directory renamed |
| T35 | zsh's default prompt ends in `%` | Run: `zsh -f` |
| T36 | `command_search.py` prints the lookup it models | Run: `command_search.py` (a model, not a shell) |
| T37 | A login shell is one whose argument zero starts with `-` or one started with `--login`; an interactive shell has its input and error output connected to terminals, and is not running a script or `-c` | Quote: Bash Reference Manual §6.1, §6.3.1 |
| T38 | The exact message of a Python workspace that is not set up | Repo: `cli/src/coding_study/adapters/languages/python/runner.py`. Run |

## Package managers

| # | Claim | Source |
|---|-------|--------|
| K1 | Homebrew's install command; the script says what it will do and waits for confirmation | Quote: [brew.sh](https://brew.sh/); [Homebrew installation](https://docs.brew.sh/Installation) |
| K2 | The installer prints directions for the shell config, `eval "$(<prefix>/bin/brew shellenv)"`, and without them Homebrew will not work | Quote: Homebrew installation |
| K3 | Prefixes: `/opt/homebrew` on Apple silicon, `/usr/local` on Intel (legacy), `/home/linuxbrew/.linuxbrew` on Linux | Quote: [Homebrew FAQ](https://docs.brew.sh/FAQ); [Homebrew on Linux](https://docs.brew.sh/Homebrew-on-Linux) |
| K4 | Each package goes into its own keg in the Cellar and is linked into the prefix; casks install pre-built binaries such as applications, fonts and plugins | Quote: brew.sh |
| K5 | `install`, `uninstall`, `update`, `upgrade`, `search` (substring of names), `list`, `deps --tree`, `doctor`, `cleanup` (removes old versions); after an install or upgrade, `brew cleanup` runs for those packages, and every 30 days for all packages | Quote: [Homebrew manual page](https://docs.brew.sh/Manpage) |
| K6 | Homebrew runs installs as the account that owns it, which is why not `sudo` | Quote: Homebrew FAQ |
| K7 | Homebrew supports WSL 2 and recommends moving off WSL 1 | Quote: Homebrew on Linux |
| K8 | APT is Ubuntu's package manager; `apt update` refreshes the database; `apt upgrade` installs newer versions; `apt install` also installs dependencies; `sudo` gives administrator rights for one command; `apt remove`, `apt search`, `apt show` | Quote: [Ubuntu Server, managing your software](https://ubuntu.com/server/docs/tutorial/managing-software/) |
| K9 | `apt` is Debian's high-level command-line interface; `remove` keeps configuration files and `purge` removes them | Quote: [apt(8) on Debian](https://manpages.debian.org/trixie/apt/apt.8.en.html) |
| K10 | `dnf install` ensures packages and their dependencies are installed; `dnf upgrade` with no argument upgrades everything; `dnf search` looks in names and summaries; `dnf remove` removes unused dependencies by default | Quote: DNF5 [install](https://dnf5.readthedocs.io/en/latest/commands/install.8.html), [upgrade](https://dnf5.readthedocs.io/en/latest/commands/upgrade.8.html), [search](https://dnf5.readthedocs.io/en/latest/commands/search.8.html), [remove](https://dnf5.readthedocs.io/en/latest/commands/remove.8.html) |
| K11 | Fedora 41 made DNF5 the default, with `dnf` and `yum` pointing at it | Quote: [Fedora change, switch to DNF5](https://fedoraproject.org/wiki/Changes/SwitchToDnf5); [Fedora Magazine, Fedora Linux 41](https://fedoramagazine.org/announcing-fedora-linux-41/) |
| K12 | WSL needs Windows 10 version 2004 (build 19041) or later, or Windows 11; `wsl --install` in an administrator PowerShell, then restart; Ubuntu by default, `-d` for another; the first start unpacks files and asks for a user name and password; Windows Terminal is recommended; new installs use WSL 2 | Quote: [Install WSL](https://learn.microsoft.com/en-us/windows/wsl/install) |
| K13 | uv is "An extremely fast Python package and project manager"; its standalone installer command; resolution picks versions that fulfil the requirements; `No solution found when resolving dependencies`; `uv.lock` holds the exact resolved versions and is managed by uv | Quote: [uv](https://docs.astral.sh/uv/), [resolution](https://docs.astral.sh/uv/concepts/resolution/), [project layout](https://docs.astral.sh/uv/concepts/projects/layout/) |
| K14 | "Cargo is the Rust package manager"; `Cargo.lock` holds exact information about dependencies and should not be edited by hand | Quote: [Cargo book](https://doc.rust-lang.org/cargo/), [Cargo.toml vs Cargo.lock](https://doc.rust-lang.org/cargo/guide/cargo-toml-vs-cargo-lock.html) |
| K15 | pnpm stores packages in a content-addressable store and links them | Quote: [pnpm motivation](https://pnpm.io/motivation) |
| K16 | "Modules are how Go manages dependencies" | Quote: [Go modules reference](https://go.dev/ref/mod) |
| K17 | The Gradle Wrapper invokes a declared version of Gradle, downloading it if needed | Quote: [Gradle Wrapper](https://docs.gradle.org/current/userguide/gradle_wrapper.html) |
| K18 | `install_order.py` prints the install orders and the packages a removal would break | Run: `install_order.py` (made-up packages) |
| K19 | cstudy's recommendations: rustup over Homebrew's Rust, the go.dev archive over a distribution's older Go, JDK 21 to 26 with Homebrew's plain `openjdk` at JDK 27, fnm, SDKMAN! and rustup as version managers; a workspace has `uv.lock` and `pnpm-lock.yaml` | Repo: [toolchains guide](../guides/toolchains.md). Run: `cstudy init` |

## Python

| # | Claim | Source |
|---|-------|--------|
| PY1 | The tutorial is "designed for programmers that are new to the Python language, not beginners who are new to programming"; its chapters 2 (interpreter), 3 (numbers, text, lists), 4 (control flow, functions), 5 (data structures), 8 (errors), 12 (virtual environments) | Quote: [The Python Tutorial](https://docs.python.org/3/tutorial/index.html) and its chapter pages |
| PY2 | The Python Wiki's Beginner's Guide for non-programmers is a community list of tutorials that "don't assume that you have previous experience"; it is a legacy page that warns "Information may be outdated or no longer applicable", and some entries are paid | Quote: [Beginner's Guide, non-programmers](https://wiki.python.org/python/getting-started/BeginnersGuide/NonProgrammers.html), linked from [Python For Beginners](https://www.python.org/about/gettingstarted/) |
| PY3 | "indentation is Python's way of grouping statements" | Quote: [tutorial §3.2](https://docs.python.org/3/tutorial/introduction.html) |
| PY4 | "The default value is evaluated only once", which matters for a mutable default | Quote: [tutorial §4.9.1](https://docs.python.org/3/tutorial/controlflow.html) |
| PY5 | Arguments are passed by object reference, so the caller sees changes to a mutable argument; a function without `return` returns `None` | Quote: tutorial §4.8 and its footnote |
| PY6 | `sorted` returns a new list; `list.copy()` returns a shallow copy | Quote: [built-in functions](https://docs.python.org/3/library/functions.html); [tutorial §5.1](https://docs.python.org/3/tutorial/datastructures.html) |
| PY7 | Appends and pops at the end are fast; inserts and pops at the front are slow; use `collections.deque` for a queue | Quote: tutorial §5.1.2 |
| PY8 | The runtime does not enforce type annotations | Quote: [`typing`](https://docs.python.org/3/library/typing.html) |
| PY9 | `list[int]` is a `GenericAlias` made by subscripting `list`; added in 3.9 | Quote: [built-in types, Generic Alias Type](https://docs.python.org/3/library/stdtypes.html) |
| PY10 | `NotImplementedError` marks an implementation that still needs to be added | Quote: [built-in exceptions](https://docs.python.org/3/library/exceptions.html) |
| PY11 | CPython lists are arrays, so indexing costs the same at any size, and appends over-allocate; dicts are resizable hash tables with O(1) lookups when the keys' hashes differ | Quote: [design and history FAQ](https://docs.python.org/3/faq/design.html) |
| PY12 | "Integers have unlimited precision" | Quote: built-in types |
| PY13 | A virtual environment is a directory tree with a Python installation and its own packages | Quote: [tutorial §12.1](https://docs.python.org/3/tutorial/venv.html) |

## TypeScript and JavaScript

| # | Claim | Source |
|---|-------|--------|
| TS1 | "you can't learn TypeScript without learning JavaScript!"; TypeScript is JavaScript's runtime with a compile-time type checker; it recommends the JavaScript guide on MDN Web Docs or Microsoft's JavaScript resources | Quote: [TypeScript for the New Programmer](https://www.typescriptlang.org/docs/handbook/typescript-from-scratch.html); [Handbook intro](https://www.typescriptlang.org/docs/handbook/intro.html) |
| TS2 | The Handbook's chapters The Basics, Everyday Types, Narrowing, More on Functions, Object Types | Quote: Handbook intro |
| TS3 | JavaScript has no separate integer type, so there is one `number`; `number[]` is an array of numbers; parameter and return annotations | Quote: [Everyday Types](https://www.typescriptlang.org/docs/handbook/2/everyday-types.html) |
| TS4 | `export` exports values from a module so that other files can import them | Quote: [MDN, export](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/export) |
| TS5 | `sort()` by default compares the elements converted to strings, sorts in place, and `(a, b) => a - b` sorts numbers; `[10, 9, 1].sort()` gives `[1, 10, 9]` | Quote: [MDN, sort](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/sort). Run: Node 24.21.0 |
| TS6 | `??` replaces only `null` and `undefined`, `\|\|` any falsy value such as `0` or `""` | Quote: [MDN, nullish coalescing](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Nullish_coalescing) |
| TS7 | `Number.MAX_SAFE_INTEGER` is 9,007,199,254,740,991 (2⁵³ − 1); `2 ** 53 + 1` prints `9007199254740992` | Quote: [MDN, MAX_SAFE_INTEGER](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Number/MAX_SAFE_INTEGER). Run: Node 24.21.0 |
| TS8 | The specification requires `Map` and `Set` access to be sublinear on average; `set.has` is on average faster than `includes` on an array of the same length | Quote: MDN [Map](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Map), [Set](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Set) |
| TS9 | Node.js replaces types with whitespace and does no type checking; type stripping is on by default since 22.18.0 and 23.6.0; only erasable syntax runs, and `enum`, namespaces with runtime code and parameter properties need transformation | Quote: [Node.js, TypeScript](https://nodejs.org/api/typescript.html) |
| TS10 | `noEmit` writes no output files, leaving TypeScript as a type checker | Quote: [TSConfig, noEmit](https://www.typescriptlang.org/tsconfig/#noEmit) |

## Java

| # | Claim | Source |
|---|-------|--------|
| J1 | dev.java's sections Your First Steps in Java (first code, IDEs, launching simple programs, JShell), Getting to Know the Language (Language Basics, Object-Oriented Programming) and Mastering the API (Collections and Streams) | Quote: [dev.java/learn](https://dev.java/learn/), [first steps](https://dev.java/learn/first-steps/), [the language](https://dev.java/learn/language/) |
| J2 | Language Basics covers variables, primitive types, arrays, operators and control flow, then numbers and strings | Quote: [Java Language Basics](https://dev.java/learn/language/constructs/basics/), [Language Basics](https://dev.java/learn/language/constructs/) |
| J3 | Since JDK 11 the `java` launcher runs a single-file program, compiling it in memory | Quote: [launching simple source-code programs](https://dev.java/learn/first-steps/first-java-code/launch-simple-source-code-programs/). Run: `java Check.java` on JDK 21 |
| J4 | `jshell` evaluates declarations, statements and expressions as you type them | Quote: [JShell](https://dev.java/learn/first-steps/first-java-code/jshell-tool/) |
| J5 | `int` holds -2147483648 to 2147483647, and "The integer operators do not indicate overflow or underflow in any way"; `Integer.MAX_VALUE + 1` is `-2147483648` | Quote: [JLS §4.2.1, §4.2.2](https://docs.oracle.com/javase/specs/jls/se21/html/jls-4.html). Run |
| J6 | An array's length is fixed when it is created; indexes start at 0 | Quote: [The Java Tutorials, arrays](https://docs.oracle.com/javase/tutorial/java/nutsandbolts/arrays.html) |
| J7 | `==` on `String` references tells whether they are the same object; `s.equals(t)` compares contents | Quote: [JLS §15.21.3](https://docs.oracle.com/javase/specs/jls/se21/html/jls-15.html). Run |
| J8 | The default `toString()` is `getClass().getName() + '@' + Integer.toHexString(hashCode())`, so an `int[]` prints as `[I@...`; `Arrays.toString` prints the contents | Quote: [Object](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Object.html), [Arrays](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Arrays.html). Run |
| J9 | `ArrayList`: `get` and `set` in constant time, `add` in amortized constant time, the rest roughly linear; `HashMap`: constant-time `get` and `put` if the hash function disperses the keys | Quote: Java 21 [ArrayList](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/ArrayList.html), [HashMap](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/HashMap.html) |
| J10 | `java.util` contains the collections framework; a type-import-on-demand declaration imports a package's accessible classes as needed | Quote: [java.util](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/package-summary.html); [JLS §7.5.2](https://docs.oracle.com/javase/specs/jls/se21/html/jls-7.html) |
| J11 | `UnsupportedOperationException` signals an unsupported operation | Quote: [UnsupportedOperationException](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/UnsupportedOperationException.html) |
| J12 | `nums[nums.length]` throws `ArrayIndexOutOfBoundsException` | Run |

## Kotlin

| # | Claim | Source |
|---|-------|--------|
| KT1 | The Kotlin tour has a beginner part, runs entirely in the browser, and needs no installation | Quote: [Kotlin tour](https://kotlinlang.org/docs/kotlin-tour-welcome.html) |
| KT2 | `fun` with typed parameters and a return type; `val` assigned once, `var` reassignable; `for`, `when`, ranges; nullable types end in `?` | Quote: [Basic syntax](https://kotlinlang.org/docs/basic-syntax.html) |
| KT3 | Koans are exercises "designed primarily for Java developers", each a failing unit test, online or in an IDE | Quote: [Kotlin Koans](https://kotlinlang.org/docs/koans.html) |
| KT4 | `IntArray` is an array of ints, `int[]` on the JVM | Quote: [IntArray](https://kotlinlang.org/api/core/kotlin-stdlib/kotlin/-int-array/) |
| KT5 | Arrays have a fixed size and no `add` or `remove`; elements are mutable in `val` and `var` arrays; `==` on arrays checks for the same object, so use `contentEquals`; primitive-type arrays avoid boxing | Quote: [Arrays](https://kotlinlang.org/docs/arrays.html) |
| KT6 | `Int` is 32 bits, -2,147,483,648 to 2,147,483,647; the compiler reports no overflow, and `2147483647 + 1` prints `-2147483648` | Quote: [Numbers](https://kotlinlang.org/docs/numbers.html) |
| KT7 | Each collection has a read-only interface, such as `List`, and a mutable one, such as `MutableList` | Quote: [Collections overview](https://kotlinlang.org/docs/collections-overview.html) |
| KT8 | Using a nullable value directly is a compiler error; safe calls with `?.` | Quote: [Null safety](https://kotlinlang.org/docs/null-safety.html) |
| KT9 | `0..<n` excludes its end | Quote: [Ranges](https://kotlinlang.org/docs/ranges.html) |
| KT10 | On the JVM, `ArrayList` and `HashMap` are typealiases of `java.util.ArrayList` and `java.util.HashMap` | Quote: [ArrayList](https://kotlinlang.org/api/core/kotlin-stdlib/kotlin.collections/-array-list/), [HashMap](https://kotlinlang.org/api/core/kotlin-stdlib/kotlin.collections/-hash-map/) |
| KT11 | `Collection<Int>.toIntArray()` returns an `IntArray` of the elements | Quote: [toIntArray](https://kotlinlang.org/api/core/kotlin-stdlib/kotlin.collections/to-int-array.html) |
| KT12 | The standard-library function in the stub always throws `NotImplementedError` (the guide cannot spell its name, `TODO`, because check G3 refuses the word) | Quote: [TODO](https://kotlinlang.org/api/core/kotlin-stdlib/kotlin/-t-o-d-o.html) |
| KT13 | `==` checks `equals()`, `===` the same object | Quote: [Equality](https://kotlinlang.org/docs/equality.html) |

## Go

| # | Claim | Source |
|---|-------|--------|
| G1 | go.dev/learn lists the Getting started tutorial, A Tour of Go (interactive, each section ending with exercises) and Effective Go | Quote: [go.dev/learn](https://go.dev/learn/) |
| G2 | The tutorial assumes some programming experience, installs Go, writes "Hello, World!" and runs it with `go run` | Quote: [Get started with Go](https://go.dev/doc/tutorial/getting-started) |
| G3 | Go's `for` unifies `for` and `while` | Quote: [Effective Go](https://go.dev/doc/effective_go) |
| G4 | `panic` creates a run-time error that stops the program | Quote: Effective Go |
| G5 | `append` allocates a new, sufficiently large array when the capacity is too small, and otherwise reuses it | Quote: [the Go specification](https://go.dev/ref/spec), Appending to and copying slices |
| G6 | An identifier may be redeclared in an inner block, where it denotes the inner entity; `:=` is a short variable declaration | Quote: the specification, Declarations and scope, Short variable declarations |
| G7 | `range` over a slice gives the index and `a[i]`; since Go 1.22 each iteration has new variables, "to avoid accidental sharing bugs" | Quote: the specification, For statements; [Go 1.22 release notes](https://go.dev/doc/go1.22) |
| G8 | `int` is either 32 or 64 bits; signed overflow is defined and "does not cause a run-time panic" | Quote: the specification, Numeric types, Integer overflow |
| G9 | "Go refuses to compile programs with unused variables or imports" | Quote: [Go FAQ](https://go.dev/doc/faq) |
| G10 | A map is a hash table with fast lookups, adds and deletes; a missing key reads as the zero value; iteration order is not specified | Quote: [Go maps in action](https://go.dev/blog/maps) |
| G11 | A slice is a descriptor of an array segment, with a length and a capacity | Quote: [Go Slices: usage and internals](https://go.dev/blog/slices-intro) |

## Rust

| # | Claim | Source |
|---|-------|--------|
| R1 | rust-lang.org/learn lists the book ("from first principles"), Rustlings and Rust By Example, and the Compiler Error Index | Quote: [rust-lang.org/learn](https://www.rust-lang.org/learn) |
| R2 | Rustlings: small exercises for reading and writing Rust, recommended in parallel with the book | Quote: [Rustlings](https://github.com/rust-lang/rustlings) |
| R3 | Ownership is "Rust's most unique feature"; the three ownership rules | Quote: [chapter 4](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html), [§4.1](https://doc.rust-lang.org/book/ch04-01-what-is-ownership.html) |
| R4 | Chapter titles: 3 Common Programming Concepts, 4 Understanding Ownership, 5 Using Structs to Structure Related Data, 6 Enums and Pattern Matching (with `Option` and `match`), 8 Common Collections (vectors, strings, hash maps) | Quote: each chapter's first page |
| R5 | Overflow panics in debug builds and wraps with `--release`; integers default to `i32`; `usize` depends on the architecture and is used for indexing; unsigned types hold 0 to 2ⁿ − 1 | Quote: [§3.2 data types](https://doc.rust-lang.org/book/ch03-02-data-types.html) |
| R6 | A vector stores values next to each other; `&v[100]` past the end panics and `v.get(100)` returns `None` | Quote: [§8.1 vectors](https://doc.rust-lang.org/book/ch08-01-vectors.html) |
| R7 | Passing a value to a function moves or copies it; a reference lets a function use a value without taking ownership; `clone` copies deeply | Quote: §4.1, [§4.2](https://doc.rust-lang.org/book/ch04-02-references-and-borrowing.html) |
| R8 | "Rust strings don't support indexing" (error E0277); `chars` and `bytes`; `to_string` and `String::from` | Quote: [§8.2 strings](https://doc.rust-lang.org/book/ch08-02-strings.html) |
| R9 | Rust has no implicit conversion between primitive types; `as` casts | Quote: [Rust By Example, casting](https://doc.rust-lang.org/rust-by-example/types/cast.html) |
| R10 | Items are private by default; `pub` makes them public | Quote: [§7.3](https://doc.rust-lang.org/book/ch07-03-paths-for-referring-to-an-item-in-the-module-tree.html) |
| R11 | `todo!()` indicates unfinished code and panics with "not yet implemented" | Quote: [todo!](https://doc.rust-lang.org/std/macro.todo.html) |
| R12 | `Vec` `get(i)` is O(1), `insert(i)` O(n − i) amortized, `remove(i)` O(n − i); `HashMap` `get`, `insert` and `remove` O(1) expected; `*` marks amortized and `~` expected costs | Quote: [std::collections](https://doc.rust-lang.org/std/collections/index.html) |
| R13 | Amortized costs average resizes over a long series of operations; `HashMap`'s expected costs can, very unlikely, be much worse because hashing is probabilistic | Quote: std::collections, Performance |

## cstudy itself

| # | Claim | Source |
|---|-------|--------|
| C1 | Every command and option the guides use: `init`, `doctor` (`--fix`), `next` (`--difficulty`), `list` (`--difficulty`, `--track`), `show`, `start` (`--lang`, `--no-open`, `--fresh`, `--timer`), `test` (`--case`, `--watch`, `--typecheck`, `--debug`), `hint`, `status`, `done` (`--rating`, `--gave-up`), `abort`, `solution` (`--all`), `history`, `learn` (`--path`, `--done`), `config edit`, `serve --open` | Run: each command's `--help`. Repo: [cli spec](../specs/cli.md) |
| C2 | The two-sum stubs in all six languages, and their paths | Run: `cstudy start two-sum --lang <language> --no-open` |
| C3 | The worked example's outputs: `next` on a new workspace, `start`, `test` with `ERROR`, `FAIL` and `TIMEOUT` (30000 ms hang guard), `hint` (1 of 3), `status`, `done --gave-up`, and the refusal of `done --rating` | Run: a scratch workspace |
| C4 | The `done --rating ok` output of a passed Python attempt; the attempt's time runs from `start` to `done` | Run: a scratch workspace. Repo: [progress and scheduling](../specs/progress-and-scheduling.md), solve time |
| C5 | Exit codes 1 (test failures), 2 (build or load failure), 3 (usage, no workspace), 4 (environment) | Repo: cli spec, Exit codes |
| C6 | `doctor` rows: `ok`, `WARN`, `FAIL` with a `fix:` hint; Go and Rust only warn; a missing Node.js, pnpm or JDK fails without stopping other languages; the `gradle` row warns | Repo: cli spec; README. Run: `cstudy doctor` |
| C7 | Grades: `--gave-up` or a solution opened before a pass is `again`; a hint caps at `ok`; over a `--timer`, or a `suboptimal` bench verdict, caps at `hard`; first reviews after 1, 2, 3 and 5 days; at most 180 days; mastered from 21 days | Repo: [progress and scheduling](../specs/progress-and-scheduling.md#grade); cli spec, Configuration |
| C8 | Every command but `init`, `doctor`, `list`, `show` and `learn` needs a workspace | Repo: cli spec, Command summary |
| C9 | The simplest approaches of `valid-palindrome` and `move-zeroes` take a few linear passes (filter, reverse and compare; filter and write back), none nested; simple Python solutions pass every case; checking every pair passes `contains-duplicate` in Python (20.5 s) and times out on `two-sum`'s generated case | Repo: their `meta.yaml`, `tests.json` and `solutions/explanation.md`. Run |
| C10 | The practice lines summarise each problem's statement or bug report | Repo: each `problem.md` |
| C11 | cstudy supports macOS and Linux, not Windows; CI runs on Ubuntu | Repo: [PRD](../prd.md) |
| C12 | 272 of 320 problems have a Python reference; the 48 without one are 17 debugging problems built on another language's trap and 31 project problems written for one other language; the four practice problems have all six languages | Run: `cstudy list --json` |
| C13 | The TypeScript runner uses Node's type stripping, and cstudy needs Node 24 or newer; `--typecheck` runs `pnpm exec tsc --noEmit` | Repo: toolchains guide; cli spec |
| C14 | Rust builds use the release profile with `overflow-checks = true`, so an `i32` overflow panics; `--debug` uses the dev profile with the same checks; vendored crates, offline | Repo: [runners spec](../specs/runners.md); toolchains guide |
| C15 | Go builds use `GOTOOLCHAIN=local` and a pinned environment, and need no download; JDK selection by `JAVA_HOME`, else the first `java` on `PATH`; Kotlin compiles through the Gradle plugin | Repo: toolchains guide |
| C16 | `cstudy start` opens `$VISUAL` or `$EDITOR`; `default_lang` is `python` | Repo: README; cli spec, Configuration |
| C17 | `cstudy learn --path getting-started` lists 7 steps: three guides and four problems; the six language guides are linked from package managers and your first problem, not steps | Run |
| C18 | `cstudy doctor --fix` runs `uv sync`, `pnpm install` and a first Gradle build; the Python project includes `debugpy` for `cstudy test --debug`; `cstudy test` on Java and Kotlin prints a `build` line | Repo: toolchains guide, Check everything; cli spec, `cstudy test` |
| C19 | `cstudy serve --open` runs the same loop in a page on your own computer, and Ctrl-C stops it | Repo: README, Practise in the browser |
| C20 | Several easy problems take up to 10⁵ numbers, such as `missing-number` and `move-zeroes` | Repo: their `problem.md` constraints |

## Left out

| What | Why |
|------|-----|
| A default shell for Linux | No official source was found that states one for Linux in general; the guide shows `echo $SHELL` instead |
| Runnable examples in Go, Kotlin, Rust and TypeScript | Go and Rust were not installed and Kotlin has no standalone compiler here, so their code could not be run; the language pages show only the stubs cstudy writes, read from a run, and short snippets from the official documentation |
| Whether Go 1.22's per-iteration loop variables depend on the `go` line of `go.mod` | The release notes do not say; the guide states only the change |
| The contents of A Tour of Go and the Rust book's table of contents | Both pages render with JavaScript, so their text could not be read; the Rust chapters were checked one page at a time |
| Fedora's own DNF pages | docs.fedoraproject.org refused the request (access denied), so DNF5's documentation and the Fedora wiki were used |
| The old DNF staying installed as `dnf-3` | Seen only in a search excerpt of the Fedora 41 release notes |
| Homebrew "bottles", and switching back to an older version after an upgrade | Not in the pages read |
| `apt autoremove` | Not in the pages read |
| A terminal in IntelliJ IDEA, and VS Code reading your shell config files | Not checked; the guide cites only what the VS Code page says |
| Pipeline commands running "side by side" and writing no temporary file | The Bash manual says each command is a separate process connected by pipes, not more |
| macOS `ls`'s wording and exit status for a missing file | Not run on macOS; the guide says they differ a little |
| `mutableListOf` and `mutableMapOf` returning a specific class | Not in the pages read |

gnu.org refused most requests (HTTP 429), so the Bash Reference Manual was read on the Bash maintainer's site, [tiswww.case.edu](https://tiswww.case.edu/php/chet/bash/bashtop.html), which publishes the same manual.

## Independent accuracy review (2026-11-12)

The review checked all 135 links, every cstudy command and option against the CLI, and the facts above. Every link resolves and every command and option exists. These are its findings and what changed.

| Finding | Change |
|---------|--------|
| `valid-palindrome` and `move-zeroes` were said to be solved in a single pass; their simplest approaches take several | "A few passes over the input, never a loop inside a loop"; C9 corrected |
| Type stripping was given as why cstudy needs Node 24, but it is on by default since 22.18.0 and 23.6.0 | The two facts are stated separately; TS9 and C13 corrected |
| Homebrew's cleanup was described as every 30 days only | After each install or upgrade for those packages, and every 30 days for all packages; K5 corrected |
| The Beginner's Guide for non-programmers was presented as Python's own documentation | Named as the Python Wiki's community list, which warns it may be out of date and lists some paid entries; PY2 corrected |
| The quoted cstudy error message dropped the backticks around its command | Quoted exactly; T38 added |
| "A few debugging problems" did not account for the 48 problems without Python | Debugging problems built on another language's trap and project problems written for one other language; C12 corrected |
| "Every new shell starts empty" ignored the inherited environment | A new shell starts with the environment it inherited, then reads a config file |
| The path counted all six language guides, so `cstudy learn --path` sent a Python learner on to the TypeScript guide | The path has 7 steps; the language guides are linked from package managers and your first problem; C17 corrected |
| Login shell, interactive shell, exit status and process were used before they were explained | Each is defined where it first appears; T37 added |
| The language guides' Complexity sections used Big-O and amortized without saying what they mean | One plain sentence in each; R13 added for Rust's expected costs |
| The config files table said "Read by every interactive shell", which bash's `~/.bashrc` row contradicted | "Read by an interactive shell" |
| The `done --rating ok` example was a Kotlin one from the CLI spec | A real Python run; C4 corrected |
| "Skipping punctuation" undersold what `valid-palindrome` skips | "Skipping everything but letters and digits" |
| T4 was marked as a search result | The Apple page loads, so it is a quote |
