pub fn majority_element(nums: Vec<i32>) -> i32 {
    let mut candidate = nums[0];
    let mut votes = 0;
    for value in nums {
        if votes == 0 {
            candidate = value;
        }
        votes += if value == candidate { 1 } else { -1 };
    }
    candidate
}
