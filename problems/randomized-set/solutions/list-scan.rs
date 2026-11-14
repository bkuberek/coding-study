use std::collections::hash_map::RandomState;
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
    rng: XorShift,
}

impl RandomizedSet {
    pub fn new() -> Self {
        RandomizedSet {
            values: Vec::new(),
            rng: XorShift::new(),
        }
    }

    pub fn insert(&mut self, value: i32) -> bool {
        if self.values.contains(&value) {
            return false;
        }
        self.values.push(value);
        true
    }

    pub fn remove(&mut self, value: i32) -> bool {
        let Some(index) = self.values.iter().position(|&stored| stored == value) else {
            return false;
        };
        // Order does not matter: move the last value into the gap instead of shifting.
        self.values.swap_remove(index);
        true
    }

    pub fn get_random(&mut self) -> i32 {
        self.values[self.rng.below(self.values.len())]
    }
}
