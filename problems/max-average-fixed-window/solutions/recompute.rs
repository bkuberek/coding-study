pub fn max_window_average(nums: Vec<i32>, k: i32) -> f64 {
    nums.windows(k as usize)
        .map(|window| f64::from(window.iter().sum::<i32>()) / f64::from(k))
        .fold(f64::NEG_INFINITY, f64::max)
}
