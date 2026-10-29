use std::sync::atomic::{AtomicI32, Ordering};

pub struct StressCounter {
    count: AtomicI32,
}

impl StressCounter {
    pub fn new() -> Self {
        StressCounter {
            count: AtomicI32::new(0),
        }
    }

    /// Safe Rust has no data race to lose an increment with: a separate load and store do.
    pub fn increment(&self) -> i32 {
        let current = self.count.load(Ordering::Relaxed);
        self.count.store(current + 1, Ordering::Relaxed);
        current + 1
    }
}
