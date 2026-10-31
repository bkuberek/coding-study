# Probe

A crate for the runner conformance suite: `src/lib.rs` defines the entry class `Probe`, and the reference adds `tests/statuses.rs`, whose tests cover every status of a suite job, and `tests/broken.rs`, which does not compile.

`cstudy` uses `probe::Probe`. Run the tests from this folder with `cargo test`.
