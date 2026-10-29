use std::sync::{Condvar, Mutex};

pub struct ConcurrencyLimiter {
    permits: Mutex<i32>,
    released: Condvar,
}

impl ConcurrencyLimiter {
    pub fn new(limit: i32) -> Self {
        ConcurrencyLimiter {
            permits: Mutex::new(limit),
            released: Condvar::new(),
        }
    }

    pub fn acquire(&self) {
        let mut permits = self.permits.lock().unwrap();
        if *permits == 0 {
            permits = self.released.wait(permits).unwrap();
        }
        *permits -= 1;
    }

    pub fn try_acquire(&self) -> bool {
        let mut permits = self.permits.lock().unwrap();
        if *permits == 0 {
            return false;
        }
        *permits -= 1;
        true
    }

    pub fn release(&self) {
        *self.permits.lock().unwrap() += 1;
        self.released.notify_all();
    }

    pub fn available(&self) -> i32 {
        *self.permits.lock().unwrap()
    }
}
