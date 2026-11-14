//! Stock counts by item name.

use std::collections::HashMap;

use super::labels::label;
use crate::stock::labels::item_key;

/// Stock counts by item name.
pub struct Inventory {
    counts: HashMap<String, i32>,
}

impl Inventory {
    pub fn new() -> Self {
        Inventory {
            counts: HashMap::new(),
        }
    }

    pub fn add(&mut self, name: String, count: i32) -> i32 {
        let total = self.counts.entry(item_key(&name)).or_insert(0);
        *total += count;
        *total
    }

    pub fn label(&mut self, name: String) -> String {
        let count = self.counts.get(&item_key(&name)).copied().unwrap_or(0);
        label(&name, count)
    }
}
