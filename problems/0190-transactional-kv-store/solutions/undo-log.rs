use std::collections::HashMap;

pub struct TransactionalStore {
    /// The current view, open transactions included.
    data: HashMap<String, String>,
    counts: HashMap<String, i32>,
    /// One undo log per open transaction, innermost last: key to its value before the first
    /// change (`None` when the key did not exist).
    undo: Vec<HashMap<String, Option<String>>>,
    /// Permanent values per key as `(sequence, value or None)`. A commit or an outside write
    /// advances the sequence, and a snapshot remembers the sequence of its commit.
    history: HashMap<String, Vec<(u32, Option<String>)>>,
    sequence: u32,
    snapshots: Vec<u32>,
}

impl TransactionalStore {
    pub fn new() -> Self {
        TransactionalStore {
            data: HashMap::new(),
            counts: HashMap::new(),
            undo: Vec::new(),
            history: HashMap::new(),
            sequence: 0,
            snapshots: Vec::new(),
        }
    }

    // Level 1
    pub fn set(&mut self, timestamp: i64, key: String, value: String) {
        self.change(key, Some(value));
    }

    // Level 1
    pub fn get(&mut self, timestamp: i64, key: String) -> String {
        self.data.get(&key).cloned().unwrap_or_default()
    }

    // Level 1
    pub fn remove(&mut self, timestamp: i64, key: String) -> bool {
        if !self.data.contains_key(&key) {
            return false;
        }
        self.change(key, None);
        true
    }

    // Level 1
    pub fn count(&mut self, timestamp: i64, value: String) -> i32 {
        self.counts.get(&value).copied().unwrap_or(0)
    }

    // Level 2
    pub fn begin(&mut self, timestamp: i64) {
        self.undo.push(HashMap::new());
    }

    // Level 2
    pub fn rollback(&mut self, timestamp: i64) -> bool {
        let Some(log) = self.undo.pop() else {
            return false;
        };
        for (key, previous) in log {
            self.assign(&key, previous);
        }
        true
    }

    // Level 3
    pub fn depth(&mut self, timestamp: i64) -> i32 {
        self.undo.len() as i32
    }

    // Level 4
    pub fn commit(&mut self, timestamp: i64) -> i32 {
        let Some(changed) = self.undo.pop() else {
            return -1;
        };
        if let Some(enclosing) = self.undo.last_mut() {
            for (key, previous) in changed {
                enclosing.entry(key).or_insert(previous);
            }
            return 0;
        }
        self.make_permanent(changed.into_keys());
        self.snapshots.push(self.sequence);
        self.snapshots.len() as i32
    }

    // Level 4
    pub fn get_snapshot(&mut self, timestamp: i64, version: i32, key: String) -> String {
        let index = match usize::try_from(version) {
            Ok(version) if version >= 1 => version - 1,
            _ => return String::new(),
        };
        let Some(&sequence) = self.snapshots.get(index) else {
            return String::new();
        };
        let history = self.history.get(&key).map_or(&[][..], Vec::as_slice);
        let position = history.partition_point(|(entry, _)| *entry <= sequence);
        position
            .checked_sub(1)
            .and_then(|last| history[last].1.clone())
            .unwrap_or_default()
    }

    fn change(&mut self, key: String, value: Option<String>) {
        if let Some(log) = self.undo.last_mut() {
            log.entry(key.clone())
                .or_insert_with(|| self.data.get(&key).cloned());
            self.assign(&key, value);
        } else {
            self.assign(&key, value);
            self.make_permanent([key]);
        }
    }

    fn assign(&mut self, key: &str, value: Option<String>) {
        if let Some(previous) = self.data.get(key) {
            if let Some(count) = self.counts.get_mut(previous) {
                *count -= 1;
            }
        }
        match value {
            None => {
                self.data.remove(key);
            }
            Some(value) => {
                *self.counts.entry(value.clone()).or_insert(0) += 1;
                self.data.insert(key.to_string(), value);
            }
        }
    }

    fn make_permanent(&mut self, keys: impl IntoIterator<Item = String>) {
        self.sequence += 1;
        for key in keys {
            let current = self.data.get(&key).cloned();
            self.history
                .entry(key)
                .or_default()
                .push((self.sequence, current));
        }
    }
}
