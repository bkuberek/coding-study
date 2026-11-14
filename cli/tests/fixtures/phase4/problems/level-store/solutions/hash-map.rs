use std::collections::HashMap;

pub struct LevelStore {
    values: HashMap<String, String>,
}

impl LevelStore {
    pub fn new() -> Self {
        LevelStore {
            values: HashMap::new(),
        }
    }

    pub fn put(&mut self, key: String, value: String) {
        self.values.insert(key, value);
    }

    pub fn get(&mut self, key: String) -> String {
        self.values.get(&key).cloned().unwrap_or_default()
    }

    pub fn remove(&mut self, key: String) -> bool {
        self.values.remove(&key).is_some()
    }

    pub fn size(&mut self) -> i32 {
        self.values.len() as i32
    }

    pub fn keys_with_prefix(&mut self, prefix: String) -> Vec<String> {
        let mut keys: Vec<String> = self
            .values
            .keys()
            .filter(|key| key.starts_with(&prefix))
            .cloned()
            .collect();
        keys.sort();
        keys
    }
}
