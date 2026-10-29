// In-Memory Database. Statement: .statements/in-memory-db.md. Run: cstudy test in-memory-db

pub struct InMemoryDb {}

impl InMemoryDb {
    pub fn new() -> Self {
        InMemoryDb {}
    }

    // Level 1
    pub fn set(&mut self, timestamp: i64, key: String, field: String, value: String) {
        todo!()
    }

    // Level 1
    pub fn get(&mut self, timestamp: i64, key: String, field: String) -> String {
        todo!()
    }

    // Level 2
    pub fn scan_by_prefix(&mut self, timestamp: i64, key: String, prefix: String) -> Vec<String> {
        todo!()
    }
}
