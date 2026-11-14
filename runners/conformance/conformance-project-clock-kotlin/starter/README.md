# Inbox

A Kotlin project for the runner conformance suite on the virtual clock: `src/main/kotlin/inbox/Inbox.kt` defines the entry class `inbox.Inbox`, whose waiting methods are `suspend` functions.

`cstudy` loads `inbox.Inbox` and grades each case on a `kotlinx-coroutines-test` scheduler of its own, whose clock is virtual. `build.gradle.kts` applies the `cs.coroutines` plugin, which brings the coroutine libraries and the runner's bridge to the scheduler.
