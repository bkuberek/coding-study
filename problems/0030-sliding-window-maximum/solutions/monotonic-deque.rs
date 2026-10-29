use std::collections::VecDeque;

pub fn max_sliding_window(nums: Vec<i32>, k: i32) -> Vec<i32> {
    let k = k as usize;
    let mut maxima = Vec::with_capacity(nums.len() + 1 - k);
    // Positions whose values decrease from front to back; the front is the window's maximum.
    let mut candidates: VecDeque<usize> = VecDeque::new();
    for (right, &value) in nums.iter().enumerate() {
        while candidates.back().is_some_and(|&last| nums[last] <= value) {
            candidates.pop_back();
        }
        candidates.push_back(right);
        if candidates[0] + k <= right {
            candidates.pop_front();
        }
        if right + 1 >= k {
            maxima.push(nums[candidates[0]]);
        }
    }
    maxima
}
