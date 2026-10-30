pub fn find_target_sum_ways(nums: Vec<i32>, target: i32) -> i32 {
    let total: i32 = nums.iter().sum();
    // ways[index][running + total] caches the count from that state; None is unknown.
    let mut ways = vec![vec![None; 2 * total as usize + 1]; nums.len()];
    count(0, 0, total, &nums, target, &mut ways)
}

fn count(
    index: usize,
    running: i32,
    total: i32,
    nums: &[i32],
    target: i32,
    ways: &mut [Vec<Option<i32>>],
) -> i32 {
    if index == nums.len() {
        return i32::from(running == target);
    }
    let offset = (running + total) as usize;
    if let Some(known) = ways[index][offset] {
        return known;
    }
    let result = count(index + 1, running + nums[index], total, nums, target, ways)
        + count(index + 1, running - nums[index], total, nums, target, ways);
    ways[index][offset] = Some(result);
    result
}
