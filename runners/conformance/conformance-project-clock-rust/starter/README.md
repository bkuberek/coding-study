# Inbox

A crate on the virtual clock for the runner conformance suite: `src/lib.rs` defines the entry class `Inbox`, whose `async fn` methods wait on tokio's clock, which `cstudy` pauses. Tasks share one `Inbox`, so its methods take `&self`.

`cstudy` uses `inbox::Inbox`. Run the tests from this folder with `cargo test`.
