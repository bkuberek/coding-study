# ADR 0003: Gradle wrapper for Java and Kotlin

| Field | Value |
|-------|-------|
| Status | Accepted |
| Date | 2026-10-24 |
| Spec | [runners](../specs/runners.md#jvm-build-details) |
| Amended by | [ADR 0008](0008-installable-tool-and-separate-workspaces.md): the wrapper ships in the workspace template and `jvm/` includes the runners from `.cs/runtime/` |

## Context

Kotlin is not installed globally. The owner uses IntelliJ for JVM code and Neovim LSPs (jdtls, Kotlin language server), which need a real project model. Builds must be reproducible and fast enough for a tight test loop.

## Decision

- Use the system Gradle (already installed via Homebrew; `brew install gradle` on a fresh machine) once to generate the wrapper in `workspace/jvm/`; commit the wrapper. All builds use `./gradlew`.
- `workspace/jvm` is one Gradle build with subprojects `java` and `kotlin`, including `runners/jvm` as an included build.
- The Kotlin compiler comes from the Kotlin Gradle plugin, pinned in `gradle/libs.versions.toml`; no global `kotlinc`.
- The CLI compiles only the active problem's package (`-Pcs.only=<snake_slug>`) through the Gradle daemon with configuration cache, then starts a fresh JVM with the cached runtime classpath.

## Consequences

- IntelliJ and LSPs import the project with no custom configuration.
- Cold start (no daemon, first Kotlin compile) can take tens of seconds; warm runs target 3 s (Java) and 5 s (Kotlin).
- Versions are pinned in the repository, so the wrapper reproduces the build on any machine with JDK 21.
- A persistent JVM compile server remains an option if warm targets are missed (PRD Q4).

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Global `kotlinc` and `javac` with manual classpaths | No IDE project model; hand-managed dependencies |
| Maven | Slower Kotlin builds and no daemon by default |
| JBang or Kotlin scripting | Weak IDE support for multi-file practice projects |
| Gradle on every test via `gradle run` | Adds Gradle task execution on every run; a fresh `java` process on a cached classpath is faster |
