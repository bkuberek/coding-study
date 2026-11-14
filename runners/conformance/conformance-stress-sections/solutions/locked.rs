use std::sync::{Condvar, Mutex};

/// `std::sync::Mutex` hands out a guard, which cannot outlive `lock`: the lock state is a flag
/// under a mutex, with a condition variable to wait for its release.
pub struct StressMutex {
    locked: Mutex<bool>,
    released: Condvar,
}

impl StressMutex {
    pub fn new() -> Self {
        StressMutex {
            locked: Mutex::new(false),
            released: Condvar::new(),
        }
    }

    pub fn lock(&self) {
        let mut locked = self.locked.lock().unwrap();
        while *locked {
            locked = self.released.wait(locked).unwrap();
        }
        *locked = true;
    }

    pub fn unlock(&self) {
        *self.locked.lock().unwrap() = false;
        self.released.notify_one();
    }
}
