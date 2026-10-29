pub fn majority_element(mut nums: Vec<i32>) -> i32 {
    nums.sort_unstable();
    // The majority block covers more than half of the sorted positions, so it covers the middle.
    nums[nums.len() / 2]
}
