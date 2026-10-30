use std::collections::hash_map::RandomState;
use std::collections::HashMap;
use std::hash::{BuildHasher, Hasher};

/// The standard library has no random numbers: this is xorshift64, seeded from the random keys
/// that `RandomState` draws from the operating system for every hash map.
struct XorShift(u64);

impl XorShift {
    fn new() -> Self {
        // The state must never be zero, which xorshift cannot leave.
        XorShift(RandomState::new().build_hasher().finish() | 1)
    }

    fn below(&mut self, bound: usize) -> usize {
        self.0 ^= self.0 << 13;
        self.0 ^= self.0 >> 7;
        self.0 ^= self.0 << 17;
        (self.0 % bound as u64) as usize
    }
}

pub struct RandomizedSet {
    values: Vec<i32>,
    index_of: HashMap<i32, usize>,
    rng: XorShift,
}

impl RandomizedSet {
    pub fn new() -> Self {
        RandomizedSet {
            values: Vec::new(),
            index_of: HashMap::new(),
            rng: XorShift::new(),
        }
    }

    pub fn insert(&mut self, value: i32) -> bool {
        if self.index_of.contains_key(&value) {
            return false;
        }
        self.index_of.insert(value, self.values.len());
        self.values.push(value);
        true
    }

    pub fn remove(&mut self, value: i32) -> bool {
        let Some(index) = self.index_of.remove(&value) else {
            return false;
        };
        // `swap_remove` moves the last value into the gap in O(1).
        self.values.swap_remove(index);
        if let Some(&moved) = self.values.get(index) {
            // The former last value filled the gap; record its new position.
            self.index_of.insert(moved, index);
        }
        true
    }

    pub fn get_random(&mut self) -> i32 {
        self.values[self.rng.below(self.values.len())]
    }
}
