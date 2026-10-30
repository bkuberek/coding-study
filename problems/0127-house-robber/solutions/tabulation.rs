pub fn rob(nums: Vec<i32>) -> i32 {
    // best[i] is the most cash obtainable from the first i houses.
    let mut best = vec![0; nums.len() + 1];
    best[1] = nums[0];
    for i in 2..=nums.len() {
        best[i] = best[i - 1].max(best[i - 2] + nums[i - 1]);
    }
    best[nums.len()]
}
