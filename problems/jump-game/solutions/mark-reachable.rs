pub fn can_jump(nums: Vec<i32>) -> bool {
    let last = nums.len() - 1;
    // reachable[i] is true once some sequence of jumps from index 0 is known to land on i.
    let mut reachable = vec![false; nums.len()];
    reachable[0] = true;
    for i in 0..nums.len() {
        if !reachable[i] {
            continue;
        }
        if i == last {
            return true;
        }
        // Mark every index this one can jump to; the clamp keeps the range inside the array.
        reachable[i + 1..=last.min(i + nums[i] as usize)].fill(true);
    }
    reachable[last]
}
