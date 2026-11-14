pub fn contains_duplicate(mut nums: Vec<i32>) -> bool {
    nums.sort_unstable();
    nums.windows(2).any(|pair| pair[0] == pair[1])
}
