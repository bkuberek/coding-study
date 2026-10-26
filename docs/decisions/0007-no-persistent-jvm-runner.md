# ADR 0007: No persistent JVM runner in v1

| Field | Value |
|-------|-------|
| Status | Accepted |
| Date | 2026-10-25 |
| Spec | [runners](../specs/runners.md#jvm-build-details) |
| Closes | PRD Q4 |

## Context

NFR-1 sets the warm `cstudy test` p50 at 1.0 s for Python and TypeScript, 3 s for Java and 5 s for Kotlin. Every Java or Kotlin `cstudy test` compiles the active problem's package through the warm Gradle daemon (`:<lang>:csClasspath -Pcs.only=<snake_slug>`, configuration cache on), then starts a fresh `java` process on the cached runtime classpath ([ADR 0003](0003-gradle-wrapper-jvm.md)). PRD Q4 asked whether a persistent JVM, a compile server or a runner that stays up between runs, is needed to meet NFR-1.

Phase 7 measured it again with the Phase 0 method: warm `cstudy test two-sum --lang <L>` (16 cases, the hash-map reference in the stub), wall time of the whole `cstudy` process over 10 runs after one warm-up run, Apple M3 Pro on AC power, with the full catalog (185 DSA problems) in place. Other work kept the machine busy: each pass started once the 1-minute load average was below 3, or after 9 minutes of waiting, and the load rose during some runs. The p50 of each pass, with the load range during it:

| Language | Phase 0 | Pass 1 | Pass 2 | Pass 3 | Gradle step (p50 per pass) | NFR-1 | Highest p50 / target |
|----------|---------|--------|--------|--------|----------------------------|-------|----------------------|
| Python | 0.33 s | 0.65 s (load 2.8 to 3.2) | | 0.47 s (4.2 to 4.3) | | 1.0 s | 65% |
| TypeScript | 0.32 s | 0.46 s (3.2 to 3.4) | | 0.44 s (3.3 to 3.4) | | 1.0 s | 46% |
| Java | 0.89 s | 2.23 s (3.4 to 5.0; max 6.18 s) | 1.36 s (2.9 to 3.3) | 1.61 s (3.6 to 4.1) | 1.55, 0.85, 1.05 s | 3 s | 74% |
| Kotlin | 0.88 s | 1.56 s (5.0 to 5.8) | 1.85 s (2.9 to 5.4) | 1.44 s (3.6 to 3.9) | 1.00, 1.20, 0.90 s | 5 s | 37% |

The Gradle step is the `build` time `cstudy test` prints. In the quietest passes, a JVM run costs about 0.85 to 0.90 s of Gradle (the daemon's up-to-date check of an unchanged package) plus about 0.5 s for the rest, which is what Python and TypeScript take in total: starting the CLI, loading the problem, and starting and running the runner. The JVM runner itself adds under 0.1 s over the Python runner (0.51 and 0.54 s against 0.47 s).

## Decision

- No persistent JVM runner and no compile server in v1. The JVM path stays as ADR 0003 describes: the Gradle daemon with configuration cache compiles the package, then a fresh JVM runs each `cstudy test`.
- Revisit when the warm p50 of Java or Kotlin, measured with the method above while the 1-minute load stays below 3, exceeds two thirds of its NFR-1 target (2 s for Java, 3.3 s for Kotlin), or when a content track makes the Gradle step dominate (for example multi-file LLD problems).
- The lever, if it is ever needed, is the Gradle step, not the JVM start: skip Gradle when the package's sources are unchanged since the last build, or compile in-process with the `javac` API, before any resident JVM.

## Consequences

- NFR-1 holds in all four languages with room to spare: the highest p50 of any pass, under load up to 5, uses 74% of the Java target and at most 65% of the others.
- Every run keeps a fresh process, which NFR-5 and the runner protocol rely on: `System.exit` in user code, threads a concurrent stress run leaves behind (the `restart_requested` exit), static state and loaded classes never survive into the next run, and the hang guard can always kill the process group.
- No daemon lifecycle of our own: nothing to start, health-check, version-match against the workspace build or restart after a crash. The Gradle daemon is the only long-lived process, and Gradle manages it.
- The JVM still costs about 0.9 s more than Python or TypeScript per run, nearly all of it the Gradle step; that is accepted. Background load widens the spread of the JVM numbers (a 6.18 s run in pass 1), so a revisit measures on a quiet machine.

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Resident JVM runner that loads the user's classes per run in a fresh class loader | Saves the JVM start, which the measurements put under 0.1 s above the Python runner, while giving up process isolation: stress-run threads, `System.exit` and static state need custom handling, and a hang means restarting the resident process anyway |
| Compile server (in-process `javac` and the embeddable Kotlin compiler instead of Gradle) | Targets the right step, but duplicates the build the IDE uses (ADR 0003) with its own classpath and incremental compile logic; not needed while NFR-1 holds, and the first step listed in the decision is cheaper |
| Gradle continuous build (`--continuous`) behind `cstudy test --watch` | Helps only `--watch`, keeps a second Gradle client running, and its output does not fit the `cstudy test` report |
