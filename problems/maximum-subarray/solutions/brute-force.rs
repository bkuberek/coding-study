pub fn max_sub_array(nums: Vec<i32>) -> i32 {
    let mut best = nums[0];
    for start in 0..nums.len() {
        let mut total = 0;
        for &value in &nums[start..] {
            total += value;
            best = best.max(total);
        }
    }
    best
}
