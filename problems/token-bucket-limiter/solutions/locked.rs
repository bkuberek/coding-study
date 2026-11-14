use std::sync::Mutex;

struct Tokens {
    stored: i64,
    last_refill: i64,
}

/// Refills lazily: each call first adds the tokens earned since the last refill, then reads or
/// takes. One mutex makes the refill and the take a single step; the threads share the bucket,
/// so the methods take `&self`.
pub struct TokenBucket {
    capacity: i64,
    refill_per_second: i64,
    tokens: Mutex<Tokens>,
}

impl TokenBucket {
    pub fn new(capacity: i64, refill_per_second: i64) -> Self {
        TokenBucket {
            capacity,
            refill_per_second,
            tokens: Mutex::new(Tokens {
                stored: capacity,
                last_refill: 0,
            }),
        }
    }

    pub fn try_acquire(&self, timestamp: i64, tokens: i64) -> bool {
        let mut bucket = self.tokens.lock().unwrap();
        self.refill(&mut bucket, timestamp);
        if bucket.stored < tokens {
            return false;
        }
        bucket.stored -= tokens;
        true
    }

    pub fn available(&self, timestamp: i64) -> i64 {
        let mut bucket = self.tokens.lock().unwrap();
        self.refill(&mut bucket, timestamp);
        bucket.stored
    }

    fn refill(&self, bucket: &mut Tokens, timestamp: i64) {
        if timestamp <= bucket.last_refill {
            return;
        }
        let earned = (timestamp - bucket.last_refill) * self.refill_per_second;
        bucket.stored = self.capacity.min(bucket.stored + earned);
        bucket.last_refill = timestamp;
    }
}
