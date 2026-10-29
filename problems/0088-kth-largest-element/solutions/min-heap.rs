use std::cmp::Reverse;
use std::collections::BinaryHeap;

pub fn find_kth_largest(nums: Vec<i32>, k: i32) -> i32 {
    let k = k as usize;
    // The heap keeps the k largest values seen so far; its root is the smallest of them.
    let mut heap: BinaryHeap<Reverse<i32>> =
        nums[..k].iter().map(|&value| Reverse(value)).collect();
    for &value in &nums[k..] {
        if let Some(mut root) = heap.peek_mut() {
            if value > root.0 {
                *root = Reverse(value);
            }
        }
    }
    heap.peek().expect("k is at least 1").0
}
