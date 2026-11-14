use std::collections::HashSet;

pub fn first_missing_positive(nums: Vec<i32>) -> i32 {
    let present: HashSet<i32> = nums.into_iter().collect();
    // The answer is at most len(nums) + 1, so this loop runs at most n + 1 times.
    let mut candidate = 1;
    while present.contains(&candidate) {
        candidate += 1;
    }
    candidate
}
