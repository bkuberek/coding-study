pub fn first_missing_positive(mut nums: Vec<i32>) -> i32 {
    let n = nums.len();
    for i in 0..n {
        // Swap nums[i] to its home index nums[i] - 1 until the value here has no home in
        // range or its home already holds it. Every swap settles one value for good.
        while let Some(home) = home_index(nums[i], n) {
            if nums[home] == nums[i] {
                break;
            }
            nums.swap(i, home);
        }
    }
    for (i, &value) in nums.iter().enumerate() {
        if value != i as i32 + 1 {
            return i as i32 + 1;
        }
    }
    n as i32 + 1
}

/// The index where `value` belongs, if it is one of 1..=n.
fn home_index(value: i32, n: usize) -> Option<usize> {
    usize::try_from(value)
        .ok()
        .filter(|&v| (1..=n).contains(&v))
        .map(|v| v - 1)
}
