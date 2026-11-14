# Tally

A crate on the virtual clock with a stress case for the runner conformance suite: `src/tally.rs` defines the entry class `Tally`, whose `add` is an `async fn`, and keeps its counts in `src/counts.rs`; `src/lib.rs` re-exports `Tally` at the root of the crate `tally`. Worker threads share one `Tally` from level 2, so its methods take `&self`, and each worker blocks on `add` on the real clock.

`cstudy` uses `tally::Tally`. Run the tests from this folder with `cargo test`.
