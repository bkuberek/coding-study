pub fn contains_duplicate(nums: Vec<i32>) -> bool {
    for (i, value) in nums.iter().enumerate() {
        if nums[i + 1..].contains(value) {
            return true;
        }
    }
    false
}
