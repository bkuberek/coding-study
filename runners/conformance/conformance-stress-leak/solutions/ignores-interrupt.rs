use std::sync::atomic::{AtomicBool, Ordering};
use std::thread;
use std::time::Duration;

pub struct StressLeak {
    spinning: AtomicBool,
}

impl StressLeak {
    pub fn new() -> Self {
        StressLeak {
            spinning: AtomicBool::new(false),
        }
    }

    /// Never returns: a thread cannot be stopped from outside, so the runner must ask for a
    /// restart.
    pub fn spin(&self) {
        self.spinning.store(true, Ordering::SeqCst);
        loop {
            thread::sleep(Duration::from_millis(1));
        }
    }

    /// Waits until `spin` runs: a run that failed before the spinner's first op would stop it
    /// there, and leave nothing running.
    pub fn fail(&self) {
        while !self.spinning.load(Ordering::SeqCst) {
            thread::sleep(Duration::from_millis(1));
        }
        panic!("leak");
    }

    pub fn noop(&self) {}
}
