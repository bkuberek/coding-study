pub fn max_sliding_window(nums: Vec<i32>, k: i32) -> Vec<i32> {
    nums.windows(k as usize)
        .map(|window| *window.iter().max().unwrap())
        .collect()
}
