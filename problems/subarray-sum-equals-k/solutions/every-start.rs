pub fn subarray_sum(nums: Vec<i32>, k: i32) -> i32 {
    let mut count = 0;
    for start in 0..nums.len() {
        let mut total = 0;
        for &value in &nums[start..] {
            total += value;
            if total == k {
                count += 1;
            }
        }
    }
    count
}
