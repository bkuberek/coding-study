pub fn search_range(nums: Vec<i32>, target: i32) -> Vec<i32> {
    let (mut first, mut last) = (-1, -1);
    for (index, &value) in nums.iter().enumerate() {
        if value == target {
            if first == -1 {
                first = index as i32;
            }
            last = index as i32;
        }
    }
    vec![first, last]
}
