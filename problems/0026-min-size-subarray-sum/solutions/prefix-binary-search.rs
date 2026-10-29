pub fn min_sub_array_len(target: i32, nums: Vec<i32>) -> i32 {
    // prefix[i] is the sum of nums[..i]; the values are strictly increasing.
    let mut prefix = Vec::with_capacity(nums.len() + 1);
    prefix.push(0);
    for &value in &nums {
        prefix.push(prefix[prefix.len() - 1] + value);
    }
    let mut best = 0;
    for start in 0..nums.len() {
        let goal = prefix[start] + target;
        let end = start + 1 + prefix[start + 1..].partition_point(|&sum| sum < goal);
        if end < prefix.len() && (best == 0 || end - start < best) {
            best = end - start;
        }
    }
    best as i32
}
