pub fn first_missing_positive(nums: Vec<i32>) -> i32 {
    let mut candidate = 1;
    while nums.contains(&candidate) {
        candidate += 1;
    }
    candidate
}
