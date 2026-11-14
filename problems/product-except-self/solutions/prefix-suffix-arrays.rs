pub fn product_except_self(nums: Vec<i32>) -> Vec<i32> {
    let n = nums.len();
    let mut left = vec![1; n]; // left[i] is the product of nums[..i]
    for i in 1..n {
        left[i] = left[i - 1] * nums[i - 1];
    }
    let mut right = vec![1; n]; // right[i] is the product of nums[i + 1..]
    for i in (0..n.saturating_sub(1)).rev() {
        right[i] = right[i + 1] * nums[i + 1];
    }
    left.into_iter()
        .zip(right)
        .map(|(before, after)| before * after)
        .collect()
}
