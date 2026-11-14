use std::collections::BinaryHeap;

pub fn max_sliding_window(nums: Vec<i32>, k: i32) -> Vec<i32> {
    let k = k as usize;
    // `(value, position)` pairs compare by value first, so the top is the largest value.
    let mut heap = BinaryHeap::new();
    let mut maxima = Vec::with_capacity(nums.len() + 1 - k);
    for (right, &value) in nums.iter().enumerate() {
        heap.push((value, right));
        if right + 1 >= k {
            while let Some(&(largest, position)) = heap.peek() {
                if position + k > right {
                    maxima.push(largest);
                    break;
                }
                heap.pop();
            }
        }
    }
    maxima
}
