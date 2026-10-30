pub fn missing_number(nums: Vec<i32>) -> i32 {
    let n = nums.len() as i64;
    // n * (n + 1) / 2 reaches 5 * 10^9 for n = 10^5: it must be computed in i64.
    let difference = n * (n + 1) / 2 - nums.iter().map(|&value| i64::from(value)).sum::<i64>();
    difference as i32
}
