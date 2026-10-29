pub fn find_min(nums: Vec<i32>) -> i32 {
    let mut smallest = nums[0];
    for &value in &nums {
        if value < smallest {
            smallest = value;
        }
    }
    smallest
}
