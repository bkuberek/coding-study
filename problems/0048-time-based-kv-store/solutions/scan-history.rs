use std::collections::HashMap;

pub struct TimeMap {
    /// Per key, the `(timestamp, value)` writes in the order they happened.
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
        if let Some(entries) = self.history.get(&key) {
            for (written_at, value) in entries.iter().rev() {
                if *written_at <= timestamp {
                    return value.clone();
                }
            }
        }
        String::new()
    }
}
