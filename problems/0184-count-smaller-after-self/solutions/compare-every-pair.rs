pub fn count_smaller(nums: Vec<i32>) -> Vec<i32> {
    nums.iter()
        .enumerate()
        .map(|(i, value)| nums[i + 1..].iter().filter(|later| *later < value).count() as i32)
        .collect()
}
