# Bank Project

A small Java project that grows over four levels. Each level adds methods to `Bank` and builds on the code you wrote for the levels before it, so how you split the code into classes and packages is up to you and part of the exercise.

## Contract

- `src/main/java/bank/Bank.java` defines the public class `bank.Bank`. Keep the class, its package and its file where they are: `cstudy submit` loads `bank.Bank`.
- `new Bank()` takes no arguments, so `Bank` keeps a public constructor without parameters.
- Each level names the methods it adds, with their parameter and return types. Keep those methods public, with those names and types; their parameter names are yours.

Everything else is yours: grow or replace `Account`, add classes to package `bank`, add packages of your own under `src/main/java/`, and add your own tests under `src/test/java/`.

## Layout

| Path | Holds |
|------|-------|
| `src/main/java/bank/Bank.java` | `Bank`, with level 1's methods to implement |
| `src/main/java/bank/Account.java` | `Account`, a first model type |
| `src/test/java/bank/Level<n>Test.java` | The examples of each open level as JUnit 5 tests, written by `cstudy` when the level opens; yours to edit, never rewritten |
| `settings.gradle.kts`, `build.gradle.kts`, `gradle.properties`, `gradle/wrapper/` | This folder's Gradle build, on the workspace's JDK 21, Gradle and JUnit |

## Running the tests

This folder is a Gradle project of its own: open it in your IDE as one. From this folder:

```sh
../../jvm/gradlew test
../../jvm/gradlew test --tests 'bank.Level1Test.ex1'
```

From the workspace, `cstudy test bank-project-java` runs the same tests.

Gradle compiles every test class before it runs any of them. When a level opens, its test class calls methods you have not written yet, so no test runs until they exist: add each method the level names, even as a stub that throws, and the earlier levels' tests run again.

Keep the Gradle files as they are: they build with the workspace's JDK, Gradle and libraries, offline once `cstudy doctor --fix` has run, and they find the workspace by walking up to its `.cs/workspace.toml`. The folder has no `gradlew` of its own; the workspace's `jvm/gradlew` runs the build.

## Grading

Your tests are feedback only. `cstudy submit bank-project-java` grades every case of the open levels, hidden ones included, against `bank.Bank`, and opens the next level when they all pass. Grading compiles only `src/main/java`, so a test class that does not compile never blocks a submission. Editing a test file never changes a grade.
