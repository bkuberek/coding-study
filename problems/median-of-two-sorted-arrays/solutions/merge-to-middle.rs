pub fn find_median_sorted_arrays(nums1: Vec<i32>, nums2: Vec<i32>) -> f64 {
    let total = nums1.len() + nums2.len();
    let (mut i, mut j) = (0, 0);
    let (mut previous, mut current) = (0, 0);
    // Advance through the merged order until `current` is the value at position total / 2.
    for _ in 0..=total / 2 {
        previous = current;
        if j == nums2.len() || (i < nums1.len() && nums1[i] <= nums2[j]) {
            current = nums1[i];
            i += 1;
        } else {
            current = nums2[j];
            j += 1;
        }
    }
    if total % 2 == 1 {
        return f64::from(current);
    }
    f64::from(previous + current) / 2.0
}
