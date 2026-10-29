use std::sync::Mutex;

pub struct StressCounter {
    count: Mutex<i32>,
}

impl StressCounter {
    pub fn new() -> Self {
        StressCounter {
            count: Mutex::new(0),
        }
    }

    pub fn increment(&self) -> i32 {
        let mut count = self.count.lock().unwrap();
        *count += 1;
        *count
    }
}
