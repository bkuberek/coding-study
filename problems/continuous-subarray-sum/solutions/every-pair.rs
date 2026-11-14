pub fn check_subarray_sum(nums: Vec<i32>, k: i32) -> bool {
    // A sum can reach 10^14, so the running total and the modulus are 64-bit.
    let k = i64::from(k);
    for (start, &first) in nums.iter().enumerate() {
        let mut total = i64::from(first);
        for &value in &nums[start + 1..] {
            total += i64::from(value);
            if total % k == 0 {
                return true;
            }
        }
    }
    false
}
