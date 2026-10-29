use std::cmp::Ordering;
use std::collections::hash_map::RandomState;
use std::hash::BuildHasher;

/// A small xorshift generator, seeded from the standard library's randomly keyed hasher: the
/// standard library has no random number generator of its own.
struct Random(u64);

impl Random {
    fn new() -> Self {
        Random(RandomState::new().hash_one(0u8) | 1)
    }

    /// A value in `0..bound`.
    fn below(&mut self, bound: usize) -> usize {
        self.0 ^= self.0 << 13;
        self.0 ^= self.0 >> 7;
        self.0 ^= self.0 << 17;
        (self.0 % bound as u64) as usize
    }
}

pub fn find_kth_largest(nums: Vec<i32>, k: i32) -> i32 {
    let mut values = nums;
    let target = values.len() - k as usize; // the answer's index in ascending order
    let (mut low, mut high) = (0, values.len() - 1);
    let mut random = Random::new();
    loop {
        let pivot = values[low + random.below(high - low + 1)];
        // Three-way partition of values[low..=high]: < pivot | == pivot | > pivot.
        let (mut less, mut scan, mut greater) = (low, low, high);
        while scan <= greater {
            match values[scan].cmp(&pivot) {
                Ordering::Less => {
                    values.swap(less, scan);
                    less += 1;
                    scan += 1;
                }
                Ordering::Greater => {
                    values.swap(scan, greater);
                    greater -= 1;
                }
                Ordering::Equal => scan += 1,
            }
        }
        if target < less {
            high = less - 1;
        } else if target > greater {
            low = greater + 1;
        } else {
            return pivot;
        }
    }
}
