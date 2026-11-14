use std::sync::{Condvar, Mutex};

pub struct StressGate {
    open: Mutex<bool>,
    opened: Condvar,
}

impl StressGate {
    pub fn new() -> Self {
        StressGate {
            open: Mutex::new(false),
            opened: Condvar::new(),
        }
    }

    pub fn enter(&self) {
        let mut open = self.open.lock().unwrap();
        while !*open {
            open = self.opened.wait(open).unwrap();
        }
    }
}
