pub fn single_number(nums: Vec<i32>) -> i32 {
    // Pairs cancel (a ^ a == 0) in any order, so only the single value is left.
    nums.into_iter().fold(0, |result, value| result ^ value)
}
