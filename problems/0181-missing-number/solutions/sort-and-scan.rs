pub fn missing_number(mut nums: Vec<i32>) -> i32 {
    nums.sort_unstable();
    // In the sorted vector, value i sits at index i until the gap.
    for (index, &value) in nums.iter().enumerate() {
        if value != index as i32 {
            return index as i32;
        }
    }
    nums.len() as i32
}
