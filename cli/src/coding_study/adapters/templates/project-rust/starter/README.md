# {{title}}

TODO: one paragraph on what this project builds over its levels.

## Contract

- The crate `{{crate_name}}` exports the struct `{{class_name}}` at its root, from `src/lib.rs`. Keep the crate name and the export where they are: `cstudy submit` uses `{{crate_name}}::{{class_name}}`.
- `{{class_name}}::new()` takes no arguments.
- Each level names the methods it adds, with their parameters and return types. Keep those names and signatures.

Everything else is yours: add modules under `src/`, and your own tests under `tests/`.

## Running the tests

From this folder:

```sh
cargo test
```

From the workspace, `cstudy test {{slug}}` runs the same tests, each test as a process of its own.

Keep `Cargo.toml` to the package and the vendored `rust_decimal` and `chrono`, declared as the runner declares them, and keep `.cargo/config.toml`: it points crates.io at the crates `cstudy` ships, so the project builds offline.

## Grading

Your tests are feedback only. `cstudy submit {{slug}}` grades every case of the open levels, hidden ones included, and opens the next level when they all pass.
