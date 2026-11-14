pub fn find_target_sum_ways(nums: Vec<i32>, target: i32) -> i32 {
    count(0, 0, &nums, target)
}

fn count(index: usize, total: i32, nums: &[i32], target: i32) -> i32 {
    if index == nums.len() {
        return i32::from(total == target);
    }
    // Give nums[index] a plus sign, then a minus sign.
    count(index + 1, total + nums[index], nums, target)
        + count(index + 1, total - nums[index], nums, target)
}
