# {{title}}

TODO: one paragraph on what this project builds over its levels.

## Contract

- `src/main/kotlin/app/{{class_name}}.kt` defines the class `app.{{class_name}}`. Keep the class, its package and its file where they are: `cstudy submit` loads `app.{{class_name}}`.
- `{{class_name}}()` takes no arguments.
- Each level names the methods it adds, with their parameters and return types; a method that waits is a `suspend` function. Keep those names and signatures.

Everything else is yours: add classes under `src/main/kotlin/`, and your own tests under `src/test/kotlin/`.

## Running the tests

This folder is a Gradle project of its own: open it in your IDE as one. From this folder:

```sh
../../jvm/gradlew test
```

From the workspace, `cstudy test {{slug}}` runs the same tests. Keep the Gradle files as they are: they build with the workspace's JDK, Gradle and libraries, offline once `cstudy doctor --fix` has run.

## Testing on the virtual clock

`cstudy` grades and tests this project on a virtual clock: the scheduler of `kotlinx-coroutines-test`, which `build.gradle.kts` brings with the `cs.coroutines` plugin, moves time from one due task to the next, so a wait of any length takes no real time. The generated tests in `src/test/kotlin/` run each example in `runTest`; write yours the same way:

```kotlin
package app

import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.async
import kotlinx.coroutines.test.advanceTimeBy
import kotlinx.coroutines.test.currentTime
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import kotlin.test.Test
import kotlin.test.assertEquals

@OptIn(ExperimentalCoroutinesApi::class)
class WaitTest {
    @Test
    fun aWaitEndsWhenAValueArrives() =
        runTest {
            val store = {{class_name}}()
            val waiter = async { store.waitFor("a", 5000L) }
            runCurrent() // every coroutine that can run has run
            advanceTimeBy(1000) // the clock moves one second forward
            runCurrent()
            store.put("a", "x")
            assertEquals("x", waiter.await()) // the clock moves while it waits
            assertEquals(1000L, currentTime) // the virtual milliseconds since the test started
        }
}
```

Wait with `delay`, `withTimeout` and `withTimeoutOrNull` in the coroutine that calls your method, or in coroutines it starts in its own scope (`coroutineScope { launch { ... } }`): they all run on the test scheduler. Code that moves to another dispatcher (`Dispatchers.Default`, `Dispatchers.IO`) runs on the real clock, which the scheduler cannot move. When your code needs the time, read it from the scheduler in its coroutine context: `currentCoroutineContext()[TestCoroutineScheduler]?.timeSource` measures the virtual time. A wait that nothing can end is a deadlock: `cstudy submit` reports the case as `STALLED` with the operation and the virtual time at once. A coroutine your code leaves active when a test ends fails it, as `runTest` fails it, so stop background work before a case ends.

Events due at the same instant happen in no fixed order, so the expected values never depend on it.

## Grading

Your tests are feedback only. `cstudy submit {{slug}}` grades every case of the open levels, hidden ones included, and opens the next level when they all pass.
