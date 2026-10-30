pub fn missing_number(nums: Vec<i32>) -> i32 {
    // Start with n, then fold in every index and value; present numbers cancel in pairs.
    let mut result = nums.len() as i32;
    for (index, &value) in nums.iter().enumerate() {
        result ^= index as i32 ^ value;
    }
    result
}
