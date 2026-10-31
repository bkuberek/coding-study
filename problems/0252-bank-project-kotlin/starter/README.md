# Bank Project

A small Kotlin project that grows over four levels. Each level adds methods to `Bank` and builds on the code you wrote for the levels before it, so how you split the code into files, classes and packages is up to you and part of the exercise.

## Contract

- `src/main/kotlin/bank/Bank.kt` defines the class `bank.Bank`. Keep the class, its package and its file where they are: `cstudy submit` loads `bank.Bank`.
- `Bank` stays a public class, and `Bank()` takes no arguments.
- Each level names the methods it adds, with their parameter and return types. Keep those method names and types; `Long` stays `Long`, and an `Int` in its place is a different method to the grader.

Everything else is yours: grow or replace `Account.kt`, add classes and packages under `src/main/kotlin/`, and add your own tests under `src/test/kotlin/`.

## Layout

| Path | Holds |
|------|-------|
| `src/main/kotlin/bank/Bank.kt` | `Bank`, with level 1's methods to implement |
| `src/main/kotlin/bank/Account.kt` | `Account`, a first model type |
| `src/test/kotlin/bank/Level<n>Test.kt` | The examples of each open level, written by `cstudy` when the level opens; yours to edit, never rewritten |
| `settings.gradle.kts`, `build.gradle.kts`, `gradle.properties`, `gradle/wrapper/gradle-wrapper.properties` | The Gradle build: JDK 21, Kotlin and kotlin.test on JUnit 5, from the workspace |

## Running the tests

This folder is a Gradle project of its own: open it in your IDE as one. From this folder:

```sh
../../jvm/gradlew test
../../jvm/gradlew test --tests 'bank.Level1Test'
```

From the workspace, `cstudy test bank-project-kotlin` runs the same tests.

Your main and test sources form one Gradle module, so a test under `src/test/kotlin/` can reach your `internal` classes too. When a level opens, its test file calls methods you have not written yet, so the tests do not compile until those methods exist; `cstudy test bank-project-kotlin --level <n>` leaves out the files of the levels above `<n>`.

Keep the Gradle files as they are. They find the workspace by walking up to `.cs/workspace.toml` and build with its JDK, Gradle and libraries, offline once `cstudy doctor --fix` has run. There is no `gradlew` here: the workspace's `jvm/gradlew` builds this folder.

## Grading

Your tests are feedback only. `cstudy submit bank-project-kotlin` grades every case of the open levels, hidden ones included, against `Bank`, and opens the next level when they all pass. Editing a test file never changes a grade.
