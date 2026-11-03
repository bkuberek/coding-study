# {{title}}

TODO: one paragraph on what this project builds over its levels.

## Contract

- The crate `{{crate_name}}` exports the struct `{{class_name}}` at its root, from `src/lib.rs`. Keep the crate name and the export where they are: `cstudy submit` uses `{{crate_name}}::{{class_name}}`.
- `{{class_name}}::new()` takes no arguments.
- Each level names the methods it adds, with their parameters and return types; a method that waits is an `async fn`. Keep those names and signatures.
- From level 2, a case runs a wait as a task that shares the instance with the rest of the case, so every method takes `&self`, and the struct keeps its state behind a lock (`std::sync::Mutex`, or tokio's when the lock is held across an `.await`).

Everything else is yours: add modules under `src/`, and your own tests under `tests/`.

## Running the tests

From this folder:

```sh
cargo test
```

From the workspace, `cstudy test {{slug}}` runs the same tests, each test as a process of its own.

Keep `Cargo.toml` to the package and the vendored `tokio`, `rust_decimal` and `chrono`, declared as the runner declares them, and keep `.cargo/config.toml`: it points crates.io at the crates `cstudy` ships, so the project builds offline.

## Testing on the virtual clock

`cstudy` grades and tests this project on tokio's paused clock: each case runs on a current-thread runtime whose clock moves only when every task waits, and then jumps to the next due timer, so a wait of any length takes no real time. The generated tests in `tests/` run each example as a `#[tokio::test(start_paused = true)]`, with two helpers defined in the file: `settle()`, which lets every task run until each one waits without moving the clock, as `cstudy` does after each operation, and `advance(ms)`, which moves the clock and lets each timer on the way fire at its own time. Write yours the same way:

```rust
use std::sync::Arc;
use std::time::Duration;

use {{crate_name}}::{{class_name}};
use tokio::time::Instant;

async fn settle() {
    let metrics = tokio::runtime::Handle::current().metrics();
    let parked = metrics.worker_park_count(0);
    tokio::task::spawn_blocking(move || {
        while metrics.worker_park_count(0) == parked {
            std::thread::yield_now();
        }
    })
    .await
    .unwrap();
}

#[tokio::test(start_paused = true)]
async fn a_wait_ends_when_a_value_arrives() {
    let start = Instant::now();
    let store = Arc::new({{class_name}}::new());
    let waiter = tokio::spawn({
        let store = Arc::clone(&store);
        async move { store.wait_for("a".to_string(), 5000).await }
    });
    settle().await; // every task that can run has run
    tokio::time::sleep(Duration::from_millis(1000)).await; // the clock moves one second
    store.put("a".to_string(), "x".to_string());
    assert_eq!(waiter.await.unwrap(), "x"); // the clock moves while it waits
    assert_eq!(start.elapsed().as_millis(), 1000); // the virtual milliseconds since the start
}
```

Wait with `tokio::time::sleep`, `timeout` and `interval`, and read the time from `tokio::time::Instant`: they all follow the paused clock. `std::time::Instant` and `std::thread::sleep` read and wait on the real clock, which the runtime cannot move. A wait that nothing can end is a deadlock: `cstudy submit` reports the case as `STALLED` with the operation and the virtual time at once, while `cargo test` waits until `cstudy test`'s time limit ends the test. Tasks still waiting when a case ends are dropped with its runtime, so stop background work through the struct's methods when a case needs it to end.

Events due at the same instant happen in no fixed order, so the expected values never depend on it.

## Grading

Your tests are feedback only. `cstudy submit {{slug}}` grades every case of the open levels, hidden ones included, and opens the next level when they all pass.
