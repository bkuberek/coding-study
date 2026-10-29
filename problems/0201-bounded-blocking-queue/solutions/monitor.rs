use std::collections::VecDeque;
use std::sync::{Condvar, Mutex};

/// One mutex guards the values. Producers wait on `not_full` and consumers on `not_empty`, two
/// condition variables used with the same mutex; the worker threads share the queue, so the
/// methods take `&self`.
pub struct BoundedBlockingQueue {
    capacity: usize,
    values: Mutex<VecDeque<i32>>,
    not_full: Condvar,
    not_empty: Condvar,
}

impl BoundedBlockingQueue {
    pub fn new(capacity: i32) -> Self {
        let capacity = capacity as usize;
        BoundedBlockingQueue {
            capacity,
            values: Mutex::new(VecDeque::with_capacity(capacity)),
            not_full: Condvar::new(),
            not_empty: Condvar::new(),
        }
    }

    pub fn put(&self, value: i32) {
        let mut values = self.values.lock().unwrap();
        while values.len() == self.capacity {
            values = self.not_full.wait(values).unwrap();
        }
        values.push_back(value);
        self.not_empty.notify_one();
    }

    pub fn take(&self) -> i32 {
        let mut values = self.values.lock().unwrap();
        while values.is_empty() {
            values = self.not_empty.wait(values).unwrap();
        }
        let value = values.pop_front().expect("the loop waited for a value");
        self.not_full.notify_one();
        value
    }

    pub fn size(&self) -> i32 {
        self.values.lock().unwrap().len() as i32
    }
}
