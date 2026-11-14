pub fn find_median_sorted_arrays(nums1: Vec<i32>, nums2: Vec<i32>) -> f64 {
    let mut merged = [nums1, nums2].concat();
    merged.sort_unstable();
    let middle = merged.len() / 2;
    if merged.len() % 2 == 1 {
        return f64::from(merged[middle]);
    }
    f64::from(merged[middle - 1] + merged[middle]) / 2.0
}
