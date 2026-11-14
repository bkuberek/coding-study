//! The entry class, which worker threads share from level 2.

use crate::counts::Counts;

pub struct Tally {
    counts: Counts,
}

impl Tally {
    pub fn new() -> Self {
        Tally {
            counts: Counts::new(),
        }
    }

    pub fn add(&self, key: String, amount: i32) -> i32 {
        self.counts.add(key, amount)
    }

    pub fn count(&self, key: String) -> i32 {
        self.counts.of(&key)
    }

    pub fn take(&self, key: String, amount: i32) -> bool {
        self.counts.take(key, amount)
    }
}
