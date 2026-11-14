//! The counts by key; every read and write holds the mutex.

use std::collections::HashMap;
use std::sync::Mutex;

pub(crate) struct Counts {
    values: Mutex<HashMap<String, i32>>,
}

impl Counts {
    pub(crate) fn new() -> Self {
        Counts {
            values: Mutex::new(HashMap::new()),
        }
    }

    pub(crate) fn add(&self, key: String, amount: i32) -> i32 {
        let mut values = self.values.lock().unwrap();
        let count = values.entry(key).or_insert(0);
        *count += amount;
        *count
    }

    pub(crate) fn of(&self, key: &str) -> i32 {
        *self.values.lock().unwrap().get(key).unwrap_or(&0)
    }

    pub(crate) fn take(&self, key: String, amount: i32) -> bool {
        let mut values = self.values.lock().unwrap();
        let count = values.entry(key).or_insert(0);
        if *count < amount {
            return false;
        }
        *count -= amount;
        true
    }
}
