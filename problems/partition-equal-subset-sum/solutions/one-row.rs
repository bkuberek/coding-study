pub fn can_partition(nums: Vec<i32>) -> bool {
    let total: i32 = nums.iter().sum();
    if total % 2 == 1 {
        return false;
    }
    let target = (total / 2) as usize;
    // reachable[s] is true when some of the elements seen so far add up to exactly s.
    let mut reachable = vec![false; target + 1];
    reachable[0] = true;
    for &value in &nums {
        let value = value as usize;
        // Right to left, so reachable[s - value] still describes the elements before `value`.
        for s in (value..=target).rev() {
            if reachable[s - value] {
                reachable[s] = true;
            }
        }
        if reachable[target] {
            return true;
        }
    }
    reachable[target]
}
