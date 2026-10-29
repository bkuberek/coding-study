use std::collections::VecDeque;
use std::sync::{Condvar, Mutex};

pub struct BoundedBlockingQueue {
    capacity: usize,
    values: Mutex<VecDeque<i32>>,
    changed: Condvar,
}

impl BoundedBlockingQueue {
    pub fn new(capacity: i32) -> Self {
        BoundedBlockingQueue {
            capacity: capacity as usize,
            values: Mutex::new(VecDeque::new()),
            changed: Condvar::new(),
        }
    }

    pub fn put(&self, value: i32) {
        let mut values = self.values.lock().unwrap();
        if values.len() >= self.capacity {
            values = self.changed.wait(values).unwrap();
        }
        values.push_back(value);
        self.changed.notify_all();
    }

    pub fn take(&self) -> i32 {
        let mut values = self.values.lock().unwrap();
        if values.is_empty() {
            values = self.changed.wait(values).unwrap();
        }
        let value = values.pop_front().unwrap();
        self.changed.notify_all();
        value
    }

    pub fn size(&self) -> i32 {
        self.values.lock().unwrap().len() as i32
    }
}
