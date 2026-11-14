pub fn search(nums: Vec<i32>, target: i32) -> i32 {
    match nums.iter().position(|&value| value == target) {
        Some(index) => index as i32,
        None => -1,
    }
}
