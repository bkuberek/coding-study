# Bank Project

A small Rust crate that grows over four levels. Each level adds methods to `Bank` and builds on the code you wrote for the levels before it, so how you split the code into modules and types is up to you and part of the exercise.

## Contract

- The crate is named `bank`, and `Bank` is public at its root: `src/lib.rs` re-exports it from `src/bank.rs` with `pub use bank::Bank;`. Keep the crate name and the export: `cstudy submit` and the tests use `bank::Bank`. You may move `Bank` into `src/lib.rs` or another module, as long as `src/lib.rs` still makes it public at the root.
- `Bank::new()` takes no arguments.
- Each level names the methods it adds, with their parameter and return types. Keep those method names and types; every method is `pub` and takes `&mut self`, and its parameter names are yours.

Everything else is yours: grow or replace `src/account.rs`, add modules under `src/`, and add your own tests.

## Layout

| Path | Holds |
|------|-------|
| `src/lib.rs` | The crate root: the module declarations and the re-export of `Bank` |
| `src/bank.rs` | `Bank` and `Bank::new()`, with level 1's methods to implement; their `todo!()` bodies panic until you do |
| `src/account.rs` | `Account`, a first model type |
| `tests/level_<n>.rs` | The examples of each open level, written by `cstudy` when the level opens; yours to edit, never rewritten |
| `Cargo.toml` | The package `bank`, with no dependencies |
| `.cargo/config.toml` | Points crates.io at the crates the workspace ships, so nothing is downloaded |

## Running the tests

From this folder:

```sh
cargo test
cargo test --test level_1
cargo test ex1
cargo clippy --all-targets
```

From the workspace, `cstudy test bank-project-rust` runs the same tests, each test as a process of its own.

Each file under `tests/` is an integration test, a crate of its own that sees only what `bank` makes public. When a level opens, its file calls methods you have not written yet, so that file does not compile until they exist: `cargo test` then stops at the build error, while `cstudy test` reports the file as one error and runs every other test. A unit test in a `#[cfg(test)] mod tests` inside a module can reach that module's private items too.

Keep `Cargo.toml` to the package and keep `.cargo/config.toml` as it is: they build offline with what the workspace ships. `cargo test` writes `target/` and `Cargo.lock` here; the workspace's `.gitignore` leaves both out.

## Grading

Your tests are feedback only. `cstudy submit bank-project-rust` grades every case of the open levels, hidden ones included, against `Bank`, and opens the next level when they all pass. Editing a test file never changes a grade.
