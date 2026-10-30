const NOT_COMPUTED: i32 = -1;

/// The most cash obtainable from houses `house`, `house + 1`, ..., the last one.
fn best_from(house: usize, nums: &[i32], memo: &mut [i32]) -> i32 {
    if house >= nums.len() {
        return 0;
    }
    if memo[house] == NOT_COMPUTED {
        let skip = best_from(house + 1, nums, memo);
        let take = nums[house] + best_from(house + 2, nums, memo);
        memo[house] = skip.max(take);
    }
    memo[house]
}

pub fn rob(nums: Vec<i32>) -> i32 {
    let mut memo = vec![NOT_COMPUTED; nums.len()];
    best_from(0, &nums, &mut memo)
}
