# ADR 0016: Java and Kotlin run on JDK 21 to 26, within the range each problem declares

| Field | Value |
|-------|-------|
| Status | Accepted |
| Date | 2026-11-01 |
| Spec | [problem-format](../specs/problem-format.md#metayaml) (`jdk`), [authoring](../specs/authoring.md#what-cstudy-verify-checks) (S17), [cli](../specs/cli.md#cstudy-doctor) (`doctor`, the range checks of `start`, `test`, `submit` and `bench`, `list`, `next` and `show`, their `--json` documents), [runners](../specs/runners.md#jvm-build-details), [installation-and-workspaces](../specs/installation-and-workspaces.md#ide-files), [web-ui](../specs/web-ui.md#problems-view), [toolchains](../guides/toolchains.md) |
| Amends | [ADR 0003](0003-gradle-wrapper-jvm.md) (the build reproduces with any supported JDK, not with JDK 21 only), [ADR 0010](0010-ide-integration.md) (the IntelliJ project JDK is no longer `21`), [ADR 0014](0014-project-problems.md) (`cs.project` no longer pins JDK 21) |
| Builds on | [ADR 0008](0008-installable-tool-and-separate-workspaces.md), [ADR 0012](0012-go-and-rust.md), [ADR 0015](0015-local-web-ui.md) |

## Context

`cstudy` accepts exactly one JDK, 21, and no decision records why. What the code base showed:

- `cstudy doctor` fails every major version but 21, and the fix it prints installs JDK 21 (`application/doctor.py`).
- Every Gradle build pins a Java 21 toolchain: the `cs.practice` plugin of the workspace's `jvm/java` and `jvm/kotlin` projects, the `cs.project` plugin of every project folder ([ADR 0014](0014-project-problems.md)), and the runner's own modules. No toolchain resolver is configured, so a machine without a JDK 21 builds nothing, online or offline.
- Up to three JDKs take part in one run: Gradle's daemon starts from `JAVA_HOME`, else the `java` on `PATH`; javac and kotlinc compile against whichever JDK 21 toolchain detection finds; the runner starts the first `java` on `PATH`. `doctor` checks only that last one.
- The default JDK package of a common macOS package manager now installs JDK 27, so a new user fails on the obvious path.
- The pinned tools set the ceiling: Gradle 9.8.2 runs on and targets JDK 21 to 27, while Kotlin 2.4.21 targets JVM 26 at most.
- Content depends on the JDK at run time. JDK 24 stopped pinning a virtual thread to its carrier inside `synchronized` and `Object.wait` ([JEP 491](https://openjdk.org/jeps/491)); the explanations of 0200 to 0205 and the concurrency table of [problem-format](../specs/problem-format.md#models-and-language-support) describe only the behavior of JDK 21.

The owner decided (2026-11-01):

- cstudy supports more than one JDK: 21 to 26.
- A problem lists the JDK versions it needs, for a problem that uses a feature only some versions have.
- With JDK 27, a user can work only on the problems that declare they run there; otherwise 27 is not supported yet.
- Builds stay offline: nothing downloads a toolchain.

Scratch builds (not merged), with Gradle 9.8.2 and Kotlin 2.4.21, offline, on JDK 21 and JDK 27, established:

| Experiment | Result |
|------------|--------|
| Java with no toolchain and `options.release` 26, then 21, Gradle on JDK 27 | Both build: class files of major version 70, then 65, and the 65 ones run on JDK 21 |
| Kotlin with no toolchain and no explicit level, on JDK 27 | Fails: `Inconsistent JVM-target compatibility detected for tasks 'compileJava' (27) and 'compileKotlin' (26)` |
| Java `release`, Kotlin `jvmTarget` and `-Xjdk-release` at one level | Builds at 26 and at 21 on JDK 27, and at 21 on JDK 21 |
| A JDK 24 API (stream gatherers, JEP 485) compiled at level 21 on JDK 27 | javac: `cannot find symbol`; kotlinc: `Unresolved reference 'Gatherers'`. At level 26 both build |
| The level read from the build's JVM, configuration cache on, the JDK switched between runs | The cache is not reused (`configuration cache cannot be reused because JVM has changed`), and the level follows the JDK |
| `org.gradle.java.home` set to JDK 21 in the Gradle user home, `JAVA_HOME` at JDK 27 | The build runs on JDK 21. `-Dorg.gradle.java.home` on the command line outranks both |
| A Java plugin from an included build, compiled against the Kotlin Gradle plugin's API only, setting the level of a Java and a Kotlin subproject | Works on JDK 21 and 27 with the configuration cache on. Offline, the API module resolves only from a repository whose cache holds it: from Maven Central it failed, from the plugin repository that had cached it with the Kotlin plugin it passed |

## Decision

### The supported range

- **JDK 21 to 26.** 21 is the first release with final virtual threads, which the runner's `virtual` variant starts (`Thread.ofVirtual`), and the release every reference was verified on. 26 is the newest release the pinned Kotlin can target; Gradle is not the limit.
- **Supported means tested.** The two ends of the range are tested: CI runs the JVM conformance suite and the JVM slow tests on JDK 21 and on JDK 26 on every push, and before a release that changes the range or the JVM build, a full `cstudy verify` of the Java and Kotlin references passes on both ([Verification](#verification)). The versions between the ends are not run separately; a behavior change inside the range, such as JDK 24's, shows at its upper end. A JDK joins the range when the pinned Gradle runs on it, the pinned Kotlin can target it, and that gate passes on it.
- **One range, defined in two places.** Python reads it from `SUPPORTED_JDKS` in `cli/src/coding_study/domain/jdk.py`; Gradle from `jdk-minimum` and `jdk-maximum` in the runners' version catalog, `runners/jvm/gradle/libs.versions.toml`, which the runner's modules read and the plugin module builds into a resource for the plugins. A fast test keeps the two equal, as one keeps the IntelliJ JDK equal to the plugin's toolchain today. Neither side can read the other without a file read in the domain or a generator across languages.
- **JDK 25 is the one to install**, the newest long-term-support release in the range: the toolchains guide and `doctor`'s fix name it, and any JDK in the range works.

### One JDK per command: the one your shell selects

- cstudy uses the JDK that `JAVA_HOME` names, else the JDK of the first `java` on `PATH`: the Gradle wrapper's own rule, which version managers set per shell and per directory. It reads the version from the `release` file in the JDK's home, so the commands that only list problems stay within NFR-2. Only a `java` whose home it cannot see, such as a launcher stub, is asked for its home and version, once per command.
- That JDK runs everything. `doctor` reports it, the range checks below compare with it, and Gradle's daemon runs on it: cstudy sets `JAVA_HOME` in the wrapper's environment and passes `-Dorg.gradle.java.home`, which outranks a setting in the Gradle user home, so javac and kotlinc compile against it. The runner starts that JDK's `bin/java`, not the first `java` on `PATH`.
- cstudy never searches for other installed JDKs and records no choice of its own.

### No toolchain; one release level per build

- The plugins and the runner's modules set no toolchain: compiling uses the JDK the daemon runs on, as it does today when that JDK is a 21.
- **The level.** Every Java compile gets `options.release`, and every Kotlin compile `jvmTarget` and `-Xjdk-release`, at one level per build: the Gradle property `cs.release` when cstudy passes one, else the feature version of the build's JDK, capped at the top of the range. The plugins set it, so the workspace's `jvm/java` and `jvm/kotlin` projects, the project folders and an IDE's Gradle import all derive the same level from the same JDK. Kotlin needs the level set explicitly: without it, a build on JDK 27 fails.
- **Your code at your JDK's level.** The files you edit compile at that level, so a JDK 26 compiles a problem that needs only 21 with everything JDK 26 offers. One level serves every problem in `jvm/java` and `jvm/kotlin`, as an IDE imports their one source set.
- **Content at the problem's minimum.** What `cstudy verify` and `cstudy bench` build from the content (references, broken references, buggy files, generated stubs, and project starters with their reference overlays) compiles with `-Pcs.release=<the problem's minimum>`, so `cstudy verify` on any JDK in the range rejects an API or a language feature newer than the declared minimum, with no second JDK installed. These builds, under `.cs/build/`, are cstudy's own; no IDE imports them.
- **The runner's classes at the supported minimum.** The runner, support, suite and plugin modules compile at release 21, so they load on every JDK that the range or an opt-in reaches.
- **No preview features.** cstudy never passes `--enable-preview`; a problem's minimum is the release in which the feature it needs became final.

### The `jdk` field

`meta.yaml` gains `jdk`, an object with `min`, `max` or both, each a JDK feature release:

```yaml
jdk: {min: 24}    # the problem's Java and Kotlin code uses stream gatherers (JDK 24)
```

- **Defaults move with the range.** A missing bound is the bound of the supported range, so a problem without `jdk` runs on 21 to 26 now, and on the wider range of a later cstudy once the gate has passed the catalog there. An explicit bound stays where it is written.
- **What a bound means.** `min` above 21: the code needs a feature of that release. `max` below 26: the problem is known not to hold above it. `max` above 26: an opt-in, made after the author verified the problem on that newer JDK, before cstudy supports it.
- **Java and Kotlin only.** The range applies to a problem's Java and Kotlin versions, one range for both; its other languages are unaffected. A project problem, which lists one language, may declare a range only when that language is Java or Kotlin. A problem of your own workspace follows the same rules.
- **Check S17.** `jdk` appears only on a problem that lists Java or Kotlin. `min`, when given, is above the supported minimum and at most the supported maximum, which caps every level. `max`, when given, is at least the effective minimum and differs from the supported maximum, because an explicit 26 would keep the problem from following the range when it grows. `schemas/meta.schema.json` checks the shape: integers, no other keys, at least one of the two.

### Where the range applies

cstudy compares the selected JDK with a problem's range wherever it would build or run that problem's Java or Kotlin code. No JDK at all counts as outside every range:

| Surface | When the selected JDK is outside the problem's range |
|---------|------------------------------------------------------|
| `cstudy start`, `test`, `submit`, `bench` | Refused before anything is written or built, with exit 4 as for a missing toolchain: `error: two-sum runs its java version on JDK 21 to 26; JAVA_HOME selects JDK 27, which cstudy does not support yet`. The other languages, and the commands that run no code (`show`, `status`, `hint`, `solution`, `done`, `history`), are unaffected |
| `cstudy verify` | Skips the problem's Java and Kotlin with a line that names the range and the JDK; `--require-ready` counts a skip as not passed |
| `cstudy list` | Lists every problem as before and marks Java and Kotlin where the JDK cannot run them, with one footer line that names the JDK and the reason; `--lang` still filters by reference language |
| `cstudy next`, `cstudy mock` | Never pick a problem the JDK cannot run in the chosen language; when that leaves nothing, the message says so |
| `cstudy show` | The statement's header names a declared range (`Java and Kotlin: JDK 24 or newer`); nothing for the default |
| `--json` | Each `cstudy list` entry gains `jdk`, its effective range (`{"min": 21, "max": 26}`), or null without Java and Kotlin; the document gains `selected_jdk` (`version`, `feature`, `source`, `supported`), null when no JDK is found. A refused `test` or `submit` ends before the run starts, with exit 4, as any environment error does |
| Web UI | The problems table and the start dialog mark or disable Java and Kotlin from those fields, with the CLI's reason; `GET /api/v1/session` carries `selected_jdk`; the health view shows `doctor`'s rows |

`cstudy doctor` reports the selected JDK in its `java` row:

| Selected JDK | Row |
|--------------|-----|
| 21 to 26 | `ok    java 26.0.1 (JAVA_HOME)`: the version and where it came from |
| Above the range | `FAIL  java 27 (not supported yet: cstudy supports JDK 21 to 26)`, with the fix: select a JDK 21 to 26 with `JAVA_HOME`, or install JDK 25 |
| Below the range, none found, or a `JAVA_HOME` that holds no JDK | `FAIL`, saying which, with the same fix |

`doctor --fix` runs the Gradle warm-up whenever the selected JDK is 21 or newer, one above the range included, so the problems that opt in build offline too. Below 21, or without a JDK, it skips the warm-up with its `FAIL` line, as it does today when `java` does not run.

### JDK 27: not supported yet

The two outcomes the owner named are one rule. Ranges default to the supported range, so on JDK 27 every problem without an opt-in is refused, and `doctor` fails the `java` row as not supported yet. A problem that declares `max: 27` starts, compiles at level 26 and runs on JDK 27. When the pinned Kotlin can target 27 and the gate passes on it, a release raises the range to 27, every problem without a bound follows, and S17 flags each `max: 27` that the range now covers, which the same change removes.

### Content that depends on the JDK at run time

- A range describes what a problem's code needs, or what its cases, stress scenarios and broken references depend on. Each of them must hold on every JDK in the range; a problem narrows its range only when no version of its content can.
- Prose about behavior that changed inside the range names the versions it holds for (`on JDK 21 to 23, ...; from JDK 24, ...`) and never narrows a range: 0200 to 0205 keep the full range and gain such notes.
- The content audit (task T3) applies this to those explanations, to the concurrency table of problem-format and to the test fixtures, and runs D6 and D7 of every Java and Kotlin concurrent problem on JDK 26, where a broken reference that stalled only because of pinning is no longer caught.

### IDE files

- `.idea/misc.xml` names the project JDK after the selected JDK's feature version (`26`) and sets the language level to the build's level (`JDK_26`, which JDK 27 gets too), so IntelliJ's Gradle import, which runs with the project JDK, compiles as `cstudy test` does. With no JDK selected, it names the recommended `25`. `JDK_VERSION` in `adapters/ide/intellij.py`, and the test that mirrors the plugin's toolchain, go away.
- The IntelliJ launcher jar is unaffected: its class files target Java 17 and load on every supported JDK. Its maintainer-only build keeps requiring javac 21, which pins its bytes, not the range ([ADR 0010](0010-ide-integration.md)).

### Verification

- CI gains a job beside the fast checks: on Linux, with JDK 21 and with JDK 26, it runs the JVM slow tests and the conformance suite in Java and Kotlin. Until now CI ran no JDK, and every slow test was a local gate.
- Before a release that changes the range or the JVM build, the local gate adds two runs. On JDK 21 and on JDK 26: a full `cstudy verify` of the Java and Kotlin references, and a practice and a project problem end to end in each language. On a JDK above the range: `doctor` reports it as not supported yet, a problem without an opt-in is refused, and an opt-in fixture passes.

## Consequences

- Java and Kotlin practice works with any JDK 21 to 26. With JDK 27 alone, `doctor` says it is not supported yet and how to select a supported JDK.
- The top of the range is bound to the pinned Kotlin: raising it past 26 needs a Kotlin release that targets the new JDK first.
- The plugin module gains a compile-only dependency on the Kotlin Gradle plugin's API, at the workspace's Kotlin version, which the runners' build resolves from the plugin repository after Maven Central. A workspace whose `doctor --fix` already built Kotlin has it cached there and upgrades offline; a new workspace caches it in its first, online, `doctor --fix` (NFR-6).
- Existing workspaces need no migration step. The runner runtime refresh brings the new plugins; the first build after the upgrade, and after any JDK switch, recompiles and stores a new configuration cache entry; the `jvm/` template files name no JDK.
- The canonical build files that S15 compares lose their version (`// Builds with the workspace's JDK, JUnit 5 and the cstudy runner ...`), and every catalog starter, template, warm-up project and fixture changes with them. A project folder keeps the files it was started with: their comment still says JDK 21, which changes nothing in the build, and `cstudy start --restore build.gradle.kts` writes the new text. S15 also accepts the 0.9 text in a problem of your own workspace, which `cstudy new --from-template project-java` or `project-kotlin` wrote.
- `.idea/misc.xml` follows ADR 0010's rewriting rule: `cstudy ide` replaces it while it is still as written, and keeps it, with a warning, once IntelliJ or you changed it.
- Switching JDKs starts another Gradle daemon, since Gradle keeps one per JDK, and recompiles once.
- A `cstudy` command started from an IDE sees the IDE's environment, so it selects the JDK of the IDE's `JAVA_HOME`, which may differ from the terminal's.
- New surface: `jdk` in `meta.yaml`, check S17, the `cs.release` Gradle property, `jdk` and `selected_jdk` in `cstudy list --json`, `selected_jdk` in the web API's session, the new `doctor` texts, and a port through which the application asks for the selected JDK.
- Everything that says JDK 21 changes with the behavior: the toolchains guide (its JDK section becomes `#jdk`, which `doctor`'s fix links), the README, the formula's caveats (`packaging/homebrew/cstudy.rb.template`), the architecture, the workspace README, the specs above, and the statements and starter READMEs of 0251 and 0252. The website keeps its own JDK wording in its own repository; the catalog numbers it syncs do not change, since it reads `languages`, not `jdk`.

## Revisit

| Trigger | What to reconsider |
|---------|--------------------|
| A pinned Kotlin release targets JDK 27, and the gate passes on 27 | Raising the range to 27, and removing the `max: 27` opt-ins that S17 then flags |
| Users need cstudy on another JDK than the one their shell selects | A configuration key for the JDK's home, read before `JAVA_HOME` |
| A problem needs a preview feature | `--enable-preview` for that problem, which pins it to one JDK |
| A problem's Java and Kotlin versions need different ranges | Bounds per language under `jdk` |
| The supported minimum moves above 21 | The runner's modules follow it; the launcher's javac pin can stay, since its class files target 17 |
| The JVM job in CI fails intermittently | Moving the stress fixtures back to the local gate |
| IDE imports and `cstudy test` disagree in practice | Writing the level into the workspace instead of deriving it from the build's JDK |

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Keep exactly JDK 21 | The obvious install now gives 27, and no problem could use a newer feature |
| A toolchain chosen per build, or Gradle's daemon JVM criteria | Both select one exact version, offline only from the installations that detection finds: with JDK 27 alone, a toolchain of 26 cannot build. A toolchain other than the daemon's JDK also forks the compiler |
| A toolchain resolver that downloads JDKs | Builds stay offline (NFR-6, owner decision) |
| Your code compiled at each problem's minimum | `jvm/java` and `jvm/kotlin` hold every problem in one source set, so an IDE imports one level for all of them and would disagree with `cstudy test` wherever a problem's minimum differs. A JDK 26 user could not write `_` for an unused variable (JDK 22) or call `Stream.gather` (JDK 24) in the many problems that need only 21. The guarantee it buys, code that runs on every JDK of the range, matters for content, which gets it |
| Everything compiled at the supported minimum | A problem that needs a newer feature could not compile |
| The newest installed JDK in the range, found by cstudy | A search per operating system and installer, which silently overrides the user's selection while the IDE and the user's own `gradlew` keep following it |
| A JDK path recorded in the workspace | Machine-specific in a workspace that moves between machines, stale once a version manager updates the JDK, and followed by neither the IDE nor `gradlew`; version managers already pin a JDK per directory |
| A range string (`jdk: "21-26"`, `jdk: ">=24"`) | A grammar to parse and document, which the schema can check only as a pattern |
| A `requires` block for every toolchain | No other language needs a bound per problem; Go and Rust keep the workspace-wide minimums of ADR 0012 |
| Defaults written into each problem | Every problem would change whenever the range moves; moving defaults let one gate move the catalog |
| JDK 27 accepted with a warning, running everything | Behavior that changes between releases, as pinning did in 24, would go unverified; the owner chose "not supported yet" |
| Narrowing 0200 to 0205 to JDK 21 to 23 | Their code and cases hold on every JDK; only their prose changes |
| Checking the JDK with `java -version` on every command | A JVM start per command, against NFR-2's 500 ms for `cstudy list` and `cstudy next` |
| Verifying the range only on a maintainer's machine | One machine rarely holds both ends of the range, and CI ran no JDK |
| S15 ignoring comment lines in build files | Loosens a check that keeps every folder identical; accepting the one earlier text in workspace problems is narrower |
