//! A probe that answers.

/// Answers a ping.
pub struct Probe {}

impl Probe {
    pub fn new() -> Self {
        Probe {}
    }

    pub fn ping(&mut self) -> String {
        "pong".to_string()
    }
}
