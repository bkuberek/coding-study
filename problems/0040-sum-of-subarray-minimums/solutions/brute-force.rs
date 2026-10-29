const MOD: i64 = 1_000_000_007;

pub fn sum_subarray_mins(arr: Vec<i32>) -> i32 {
    let mut total: i64 = 0;
    for start in 0..arr.len() {
        // Extend the subarray one element at a time, keeping its running minimum.
        let mut lowest = arr[start];
        for &value in &arr[start..] {
            lowest = lowest.min(value);
            total += i64::from(lowest);
        }
        total %= MOD;
    }
    total as i32
}
