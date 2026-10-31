# Inventory

A multi-file crate for the runner conformance suite: `src/stock/inventory.rs` defines the entry class `Inventory`, `src/stock/labels.rs` formats labels, and `src/lib.rs` re-exports `Inventory` at the root of the crate `shop`.

`cstudy` uses `shop::Inventory`. Run the tests from this folder with `cargo test`.
