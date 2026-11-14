use std::collections::{BTreeMap, HashMap};

/// Rust's standard library has no insertion-ordered map, so recency is a counter: `by_recency`
/// orders keys by the tick of their last use, and its first entry is the least recently used.
pub struct LRUCache {
    capacity: usize,
    tick: u64,
    entries: HashMap<i32, (i32, u64)>,
    by_recency: BTreeMap<u64, i32>,
}

impl LRUCache {
    pub fn new(capacity: i32) -> Self {
        LRUCache {
            capacity: capacity as usize,
            tick: 0,
            entries: HashMap::with_capacity(capacity as usize),
            by_recency: BTreeMap::new(),
        }
    }

    pub fn get(&mut self, key: i32) -> i32 {
        self.touch(key).unwrap_or(-1)
    }

    pub fn put(&mut self, key: i32, value: i32) {
        if self.touch(key).is_some() {
            if let Some(entry) = self.entries.get_mut(&key) {
                entry.0 = value;
            }
            return;
        }
        if self.entries.len() == self.capacity {
            if let Some((_, oldest)) = self.by_recency.pop_first() {
                self.entries.remove(&oldest);
            }
        }
        self.tick += 1;
        self.entries.insert(key, (value, self.tick));
        self.by_recency.insert(self.tick, key);
    }

    /// Marks `key` as the most recently used and returns its value.
    fn touch(&mut self, key: i32) -> Option<i32> {
        let (value, used) = self.entries.get_mut(&key)?;
        self.by_recency.remove(used);
        self.tick += 1;
        *used = self.tick;
        self.by_recency.insert(self.tick, key);
        Some(*value)
    }
}
