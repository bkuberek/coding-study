pub fn max_product(nums: Vec<i32>) -> i32 {
    // Within a zero-free run, the best product is a prefix or a suffix of the run, so the
    // running products from both ends (restarted after each zero) cover every candidate.
    let mut best = nums.iter().copied().max().unwrap();
    let (mut from_left, mut from_right) = (1, 1);
    let n = nums.len();
    for i in 0..n {
        if from_left == 0 {
            from_left = 1;
        }
        if from_right == 0 {
            from_right = 1;
        }
        from_left *= nums[i];
        from_right *= nums[n - 1 - i];
        best = best.max(from_left).max(from_right);
    }
    best
}
