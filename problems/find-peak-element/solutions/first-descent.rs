pub fn find_peak_element(nums: Vec<i32>) -> i32 {
    // Before the first descent the values only rise, so the element just before it beats both
    // neighbors. With no descent at all, the last element is the peak.
    let peak = nums
        .windows(2)
        .position(|pair| pair[0] > pair[1])
        .unwrap_or(nums.len() - 1);
    peak as i32
}
