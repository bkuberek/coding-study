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

pub fn k_closest(mut points: Vec<Vec<i32>>, k: i32) -> Vec<Vec<i32>> {
    let k = k as usize;
    let distance: Vec<i32> = points
        .iter()
        .map(|point| point[0] * point[0] + point[1] * point[1])
        .collect();
    let mut order: Vec<usize> = (0..points.len()).collect();
    let (mut low, mut high) = (0, order.len() - 1);
    let mut random = Random::new();
    // Partition until position k - 1 holds its sorted entry; then positions 0..k-1 hold
    // the k closest points (in some order).
    while low < high {
        let pivot = distance[order[low + random.below(high - low + 1)]];
        let (mut less, mut scan, mut greater) = (low, low, high);
        while scan <= greater {
            match distance[order[scan]].cmp(&pivot) {
                Ordering::Less => {
                    order.swap(less, scan);
                    less += 1;
                    scan += 1;
                }
                Ordering::Greater => {
                    order.swap(scan, greater);
                    greater -= 1;
                }
                Ordering::Equal => scan += 1,
            }
        }
        if k - 1 < less {
            high = less - 1;
        } else if k - 1 > greater {
            low = greater + 1;
        } else {
            break;
        }
    }
    order[..k]
        .iter()
        .map(|&position| std::mem::take(&mut points[position]))
        .collect()
}
