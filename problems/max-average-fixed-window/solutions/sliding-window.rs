pub fn max_window_average(nums: Vec<i32>, k: i32) -> f64 {
    let width = k as usize;
    // A window sum is at most 10^5 * 10^4 = 10^9, which fits in an i32.
    let mut window_sum: i32 = nums[..width].iter().sum();
    let mut best = window_sum;
    for right in width..nums.len() {
        // Slide one step: the number at `right` enters and the one k places back leaves.
        window_sum += nums[right] - nums[right - width];
        best = best.max(window_sum);
    }
    // Every window has k numbers, so the largest sum is the largest average. Divide once.
    f64::from(best) / f64::from(k)
}
