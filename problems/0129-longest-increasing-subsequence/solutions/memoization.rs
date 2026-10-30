/// The length of the longest increasing subsequence whose first element is `nums[start]`.
fn longest_from(start: usize, nums: &[i32], memo: &mut [i32]) -> i32 {
    if memo[start] == 0 {
        let mut best = 1;
        for following in start + 1..nums.len() {
            if nums[following] > nums[start] {
                best = best.max(1 + longest_from(following, nums, memo));
            }
        }
        memo[start] = best;
    }
    memo[start]
}

pub fn length_of_lis(nums: Vec<i32>) -> i32 {
    // 0 means "not computed yet": every start has length at least 1.
    let mut memo = vec![0; nums.len()];
    (0..nums.len())
        .map(|start| longest_from(start, &nums, &mut memo))
        .max()
        .unwrap_or(0)
}
