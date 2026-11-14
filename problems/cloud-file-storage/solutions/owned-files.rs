use std::cmp::Ordering;
use std::collections::{HashMap, HashSet};

#[derive(Clone)]
struct File {
    name: String,
    size: i64,
    owner: Option<String>,
}

struct User {
    capacity: i64,
    used: i64,
    files: HashSet<String>,
}

impl User {
    fn fits(&self, size: i64) -> bool {
        self.used + size <= self.capacity
    }
}

fn largest_first(a: &File, b: &File) -> Ordering {
    b.size.cmp(&a.size).then_with(|| a.name.cmp(&b.name))
}

pub struct CloudStorage {
    files: HashMap<String, File>,
    users: HashMap<String, User>,
    backups: HashMap<String, Vec<File>>,
}

impl CloudStorage {
    pub fn new() -> Self {
        CloudStorage {
            files: HashMap::new(),
            users: HashMap::new(),
            backups: HashMap::new(),
        }
    }

    // Level 1
    pub fn add_file(&mut self, timestamp: i64, name: String, size: i64) -> bool {
        if self.files.contains_key(&name) {
            return false;
        }
        self.store(File {
            name,
            size,
            owner: None,
        });
        true
    }

    // Level 1
    pub fn get_file_size(&mut self, timestamp: i64, name: String) -> i64 {
        self.files.get(&name).map_or(-1, |file| file.size)
    }

    // Level 1
    pub fn delete_file(&mut self, timestamp: i64, name: String) -> i64 {
        match self.discard(&name) {
            Some(file) => file.size,
            None => -1,
        }
    }

    // Level 2
    pub fn list_largest(&mut self, timestamp: i64, prefix: String, limit: i32) -> Vec<String> {
        let mut matching: Vec<&File> = self
            .files
            .values()
            .filter(|file| file.name.starts_with(&prefix))
            .collect();
        matching.sort_by(|a, b| largest_first(a, b));
        matching
            .into_iter()
            .take(usize::try_from(limit).unwrap_or(0))
            .map(|file| format!("{}({})", file.name, file.size))
            .collect()
    }

    // Level 3
    pub fn add_user(&mut self, timestamp: i64, user_id: String, capacity: i64) -> bool {
        if self.users.contains_key(&user_id) {
            return false;
        }
        self.users.insert(
            user_id,
            User {
                capacity,
                used: 0,
                files: HashSet::new(),
            },
        );
        true
    }

    // Level 3
    pub fn add_file_by(&mut self, timestamp: i64, user_id: String, name: String, size: i64) -> i64 {
        let Some(user) = self.users.get(&user_id) else {
            return -1;
        };
        if self.files.contains_key(&name) || !user.fits(size) {
            return -1;
        }
        self.store(File {
            name,
            size,
            owner: Some(user_id.clone()),
        });
        let user = &self.users[&user_id];
        user.capacity - user.used
    }

    // Level 3
    pub fn update_capacity(&mut self, timestamp: i64, user_id: String, capacity: i64) -> i32 {
        let Some(user) = self.users.get_mut(&user_id) else {
            return -1;
        };
        user.capacity = capacity;
        let mut owned = self.owned_by(&user_id);
        owned.sort_by(largest_first);
        let mut removed = 0;
        for file in owned {
            if self.users[&user_id].used <= capacity {
                break;
            }
            self.discard(&file.name);
            removed += 1;
        }
        removed
    }

    // Level 4
    pub fn backup_user(&mut self, timestamp: i64, user_id: String) -> i32 {
        if !self.users.contains_key(&user_id) {
            return -1;
        }
        let owned = self.owned_by(&user_id);
        let count = owned.len() as i32;
        self.backups.insert(user_id, owned);
        count
    }

    // Level 4
    pub fn restore_user(&mut self, timestamp: i64, user_id: String) -> i32 {
        if !self.users.contains_key(&user_id) {
            return -1;
        }
        for file in self.owned_by(&user_id) {
            self.discard(&file.name);
        }
        let mut saved = self.backups.get(&user_id).cloned().unwrap_or_default();
        saved.sort_by(|a, b| a.name.cmp(&b.name));
        let mut restored = 0;
        for file in saved {
            if !self.files.contains_key(&file.name) && self.users[&user_id].fits(file.size) {
                self.store(file);
                restored += 1;
            }
        }
        restored
    }

    fn owned_by(&self, user_id: &str) -> Vec<File> {
        self.users[user_id]
            .files
            .iter()
            .map(|name| self.files[name].clone())
            .collect()
    }

    fn store(&mut self, file: File) {
        if let Some(user) = file.owner.as_ref().and_then(|id| self.users.get_mut(id)) {
            user.used += file.size;
            user.files.insert(file.name.clone());
        }
        self.files.insert(file.name.clone(), file);
    }

    fn discard(&mut self, name: &str) -> Option<File> {
        let file = self.files.remove(name)?;
        if let Some(user) = file.owner.as_ref().and_then(|id| self.users.get_mut(id)) {
            user.used -= file.size;
            user.files.remove(name);
        }
        Some(file)
    }
}
