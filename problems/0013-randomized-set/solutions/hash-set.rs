use std::collections::hash_map::RandomState;
use std::collections::HashSet;
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
    values: HashSet<i32>,
    rng: XorShift,
}

impl RandomizedSet {
    pub fn new() -> Self {
        RandomizedSet {
            values: HashSet::new(),
            rng: XorShift::new(),
        }
    }

    pub fn insert(&mut self, value: i32) -> bool {
        self.values.insert(value)
    }

    pub fn remove(&mut self, value: i32) -> bool {
        self.values.remove(&value)
    }

    pub fn get_random(&mut self) -> i32 {
        // A set has no positions: walk its iteration order to a random rank, O(n).
        let rank = self.rng.below(self.values.len());
        *self
            .values
            .iter()
            .nth(rank)
            .expect("getRandom on an empty set")
    }
}
