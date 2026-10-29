pub fn product_except_self(nums: Vec<i32>) -> Vec<i32> {
    (0..nums.len())
        .map(|i| nums[..i].iter().product::<i32>() * nums[i + 1..].iter().product::<i32>())
        .collect()
}
