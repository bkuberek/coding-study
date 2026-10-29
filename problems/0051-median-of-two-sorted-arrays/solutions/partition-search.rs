pub fn find_median_sorted_arrays(nums1: Vec<i32>, nums2: Vec<i32>) -> f64 {
    let (shorter, longer) = if nums1.len() <= nums2.len() {
        (&nums1, &nums2)
    } else {
        (&nums2, &nums1)
    };
    let total = shorter.len() + longer.len();
    let lower_size = total.div_ceil(2);
    let (mut low, mut high) = (0, shorter.len());
    while low <= high {
        // Take `take_short` values from `shorter` and the rest of the lower half from `longer`.
        let take_short = low + (high - low) / 2;
        let take_long = lower_size - take_short;
        let (short_left, short_right) = neighbors(shorter, take_short);
        let (long_left, long_right) = neighbors(longer, take_long);
        if short_left > long_right {
            // Only a cut with something on its left can be too far right, so `take_short >= 1`.
            high = take_short - 1;
        } else if long_left > short_right {
            low = take_short + 1;
        } else {
            let lower_max = short_left.max(long_left);
            if total % 2 == 1 {
                return f64::from(lower_max);
            }
            let upper_min = short_right.min(long_right);
            return (f64::from(lower_max) + f64::from(upper_min)) / 2.0;
        }
    }
    panic!("the arrays must be sorted")
}

/// The values just before and just after a cut at position `cut`, with `i32::MIN` and
/// `i32::MAX` where the cut has no neighbor on that side.
fn neighbors(nums: &[i32], cut: usize) -> (i32, i32) {
    let left = if cut > 0 { nums[cut - 1] } else { i32::MIN };
    let right = nums.get(cut).copied().unwrap_or(i32::MAX);
    (left, right)
}
