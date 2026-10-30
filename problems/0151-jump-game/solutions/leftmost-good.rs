pub fn can_jump(nums: Vec<i32>) -> bool {
    // The leftmost index known to reach the last index.
    let mut goal = nums.len() - 1;
    // Every index before the last one, from right to left; empty for a single element.
    for i in (0..goal).rev() {
        if i + nums[i] as usize >= goal {
            goal = i;
        }
    }
    goal == 0
}
