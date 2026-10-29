use std::sync::atomic::{AtomicI64, Ordering};

pub struct TokenBucket {
    capacity: i64,
    refill_per_second: i64,
    stored: AtomicI64,
    last_refill: AtomicI64,
}

impl TokenBucket {
    pub fn new(capacity: i64, refill_per_second: i64) -> Self {
        TokenBucket {
            capacity,
            refill_per_second,
            stored: AtomicI64::new(capacity),
            last_refill: AtomicI64::new(0),
        }
    }

    pub fn try_acquire(&self, timestamp: i64, tokens: i64) -> bool {
        self.refill(timestamp);
        let stored = self.stored.load(Ordering::SeqCst);
        if stored < tokens {
            return false;
        }
        self.stored.store(stored - tokens, Ordering::SeqCst);
        true
    }

    pub fn available(&self, timestamp: i64) -> i64 {
        self.refill(timestamp);
        self.stored.load(Ordering::SeqCst)
    }

    fn refill(&self, timestamp: i64) {
        let last_refill = self.last_refill.load(Ordering::SeqCst);
        if timestamp <= last_refill {
            return;
        }
        let earned = (timestamp - last_refill) * self.refill_per_second;
        let stored = self.stored.load(Ordering::SeqCst);
        self.stored
            .store(self.capacity.min(stored + earned), Ordering::SeqCst);
        self.last_refill.store(timestamp, Ordering::SeqCst);
    }
}
