use std::collections::HashMap;

pub struct TimeMap {
    /// Per key, the `(timestamp, value)` writes sorted by timestamp (they arrive in time order).
    history: HashMap<String, Vec<(i32, String)>>,
}

impl TimeMap {
    pub fn new() -> Self {
        TimeMap {
            history: HashMap::new(),
        }
    }

    pub fn set(&mut self, key: String, value: String, timestamp: i32) {
        self.history
            .entry(key)
            .or_default()
            .push((timestamp, value));
    }

    pub fn get(&mut self, key: String, timestamp: i32) -> String {
        let Some(entries) = self.history.get(&key) else {
            return String::new();
        };
        // Number of writes at or before timestamp; the last of them is the answer.
        let count = entries.partition_point(|&(written_at, _)| written_at <= timestamp);
        match count {
            0 => String::new(),
            _ => entries[count - 1].1.clone(),
        }
    }
}
