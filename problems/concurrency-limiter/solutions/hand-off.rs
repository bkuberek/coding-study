use std::sync::{Condvar, Mutex};

/// Waiting workers draw tickets in arrival order. A release with workers waiting hands its
/// permit to the oldest ticket by raising `granted_below`, so a newcomer can never take the
/// permit in between; every waiter re-checks its own ticket after a wake-up.
struct Permits {
    free: i32,
    next_ticket: u64,
    /// Every ticket below this one holds a permit.
    granted_below: u64,
}

pub struct ConcurrencyLimiter {
    permits: Mutex<Permits>,
    handed_off: Condvar,
}

impl ConcurrencyLimiter {
    pub fn new(limit: i32) -> Self {
        ConcurrencyLimiter {
            permits: Mutex::new(Permits {
                free: limit,
                next_ticket: 0,
                granted_below: 0,
            }),
            handed_off: Condvar::new(),
        }
    }

    pub fn acquire(&self) {
        let mut permits = self.permits.lock().unwrap();
        if permits.free > 0 {
            permits.free -= 1;
            return;
        }
        let ticket = permits.next_ticket;
        permits.next_ticket += 1;
        while ticket >= permits.granted_below {
            permits = self.handed_off.wait(permits).unwrap();
        }
    }

    pub fn try_acquire(&self) -> bool {
        let mut permits = self.permits.lock().unwrap();
        if permits.free == 0 {
            return false;
        }
        permits.free -= 1;
        true
    }

    pub fn release(&self) {
        let mut permits = self.permits.lock().unwrap();
        if permits.granted_below == permits.next_ticket {
            permits.free += 1;
            return;
        }
        permits.granted_below += 1;
        self.handed_off.notify_all();
    }

    pub fn available(&self) -> i32 {
        self.permits.lock().unwrap().free
    }
}
