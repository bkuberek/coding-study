# {{title}}

TODO: one paragraph on what this project builds over its levels.

## Contract

- `src/main/kotlin/app/{{class_name}}.kt` defines the class `app.{{class_name}}`. Keep the class, its package and its file where they are: `cstudy submit` loads `app.{{class_name}}`.
- `{{class_name}}()` takes no arguments.
- Each level names the methods it adds, with their parameters and return types. Keep those names and signatures.

Everything else is yours: add classes under `src/main/kotlin/`, and your own tests under `src/test/kotlin/`.

## Running the tests

This folder is a Gradle project of its own: open it in your IDE as one. From this folder:

```sh
../../jvm/gradlew test
```

From the workspace, `cstudy test {{slug}}` runs the same tests. Keep the Gradle files as they are: they build with the workspace's JDK, Gradle and libraries, offline once `cstudy doctor --fix` has run.

## Grading

Your tests are feedback only. `cstudy submit {{slug}}` grades every case of the open levels, hidden ones included, and opens the next level when they all pass.
