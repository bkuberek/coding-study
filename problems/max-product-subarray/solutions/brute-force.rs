pub fn max_product(nums: Vec<i32>) -> i32 {
    let mut best = nums[0];
    for start in 0..nums.len() {
        let mut product = 1;
        for &value in &nums[start..] {
            product *= value;
            best = best.max(product);
        }
    }
    best
}
