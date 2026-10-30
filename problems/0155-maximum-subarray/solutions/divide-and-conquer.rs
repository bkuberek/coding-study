pub fn max_sub_array(nums: Vec<i32>) -> i32 {
    best_in(&nums, 0, nums.len() - 1)
}

// The best subarray sum within nums[low..=high].
fn best_in(nums: &[i32], low: usize, high: usize) -> i32 {
    if low == high {
        return nums[low];
    }
    let middle = (low + high) / 2;
    // The best crossing subarray is a best suffix of the left half plus a best prefix of the
    // right half.
    let mut left_suffix = nums[middle];
    let mut total = 0;
    for &value in nums[low..=middle].iter().rev() {
        total += value;
        left_suffix = left_suffix.max(total);
    }
    let mut right_prefix = nums[middle + 1];
    total = 0;
    for &value in &nums[middle + 1..=high] {
        total += value;
        right_prefix = right_prefix.max(total);
    }
    best_in(nums, low, middle)
        .max(best_in(nums, middle + 1, high))
        .max(left_suffix + right_prefix)
}
