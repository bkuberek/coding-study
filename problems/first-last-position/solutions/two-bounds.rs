pub fn search_range(nums: Vec<i32>, target: i32) -> Vec<i32> {
    let first = first_index(&nums, |value| value >= target);
    if first == nums.len() || nums[first] != target {
        return vec![-1, -1];
    }
    let past_last = first_index(&nums, |value| value > target);
    vec![first as i32, past_last as i32 - 1]
}

/// The smallest index whose value satisfies the monotone predicate `is_past`, or `nums.len()`.
fn first_index(nums: &[i32], is_past: impl Fn(i32) -> bool) -> usize {
    let (mut low, mut high) = (0, nums.len());
    while low < high {
        let middle = low + (high - low) / 2;
        if is_past(nums[middle]) {
            high = middle;
        } else {
            low = middle + 1;
        }
    }
    low
}
