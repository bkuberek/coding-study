# Tally

A crate with a stress case for the runner conformance suite: `src/tally.rs` defines the entry class `Tally`, which keeps its counts in `src/counts.rs`, and `src/lib.rs` re-exports `Tally` at the root of the crate `tally`. Worker threads share one `Tally` from level 2, so its methods take `&self`.

`cstudy` uses `tally::Tally`. Run the tests from this folder with `cargo test`.
