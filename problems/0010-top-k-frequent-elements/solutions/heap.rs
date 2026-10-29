use std::cmp::Reverse;
use std::collections::{BinaryHeap, HashMap};

pub fn top_k_frequent(nums: Vec<i32>, k: i32) -> Vec<i32> {
    let k = k as usize;
    let mut counts: HashMap<i32, usize> = HashMap::new();
    for value in nums {
        *counts.entry(value).or_insert(0) += 1;
    }
    // `BinaryHeap` is a max-heap: wrapping the entries in `Reverse` makes its root the weakest
    // of the k entries kept so far.
    let mut heap: BinaryHeap<Reverse<(usize, i32)>> = BinaryHeap::with_capacity(k);
    for (value, count) in counts {
        if heap.len() < k {
            heap.push(Reverse((count, value)));
        } else if let Some(mut weakest) = heap.peek_mut() {
            let Reverse((weakest_count, _)) = *weakest;
            if count > weakest_count {
                *weakest = Reverse((count, value));
            }
        }
    }
    heap.into_iter().map(|Reverse((_, value))| value).collect()
}
