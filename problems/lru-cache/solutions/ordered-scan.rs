pub struct LRUCache {
    capacity: usize,
    /// `(key, value)` pairs from least to most recently used.
    entries: Vec<(i32, i32)>,
}

impl LRUCache {
    pub fn new(capacity: i32) -> Self {
        LRUCache {
            capacity: capacity as usize,
            entries: Vec::with_capacity(capacity as usize),
        }
    }

    pub fn get(&mut self, key: i32) -> i32 {
        match self.position(key) {
            Some(index) => {
                let entry = self.entries.remove(index);
                self.entries.push(entry);
                entry.1
            }
            None => -1,
        }
    }

    pub fn put(&mut self, key: i32, value: i32) {
        if let Some(index) = self.position(key) {
            self.entries.remove(index);
        } else if self.entries.len() == self.capacity {
            self.entries.remove(0);
        }
        self.entries.push((key, value));
    }

    fn position(&self, key: i32) -> Option<usize> {
        self.entries.iter().position(|&(stored, _)| stored == key)
    }
}
