pub fn majority_element(nums: Vec<i32>) -> i32 {
    let half = nums.len() / 2;
    for &candidate in &nums {
        if nums.iter().filter(|&&value| value == candidate).count() > half {
            return candidate;
        }
    }
    panic!("no majority element");
}
