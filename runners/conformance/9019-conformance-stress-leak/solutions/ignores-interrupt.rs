use std::thread;
use std::time::Duration;

pub struct StressLeak {}

impl StressLeak {
    pub fn new() -> Self {
        StressLeak {}
    }

    /// Never returns: a thread cannot be stopped from outside, so the runner must ask for a
    /// restart.
    pub fn spin(&self) {
        loop {
            thread::sleep(Duration::from_millis(1));
        }
    }

    pub fn fail(&self) {
        panic!("leak");
    }

    pub fn noop(&self) {}
}
