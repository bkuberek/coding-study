pub fn search_insert(nums: Vec<i32>, target: i32) -> i32 {
    // In a sorted array, target belongs right after every smaller value.
    nums.iter().filter(|&&value| value < target).count() as i32
}
