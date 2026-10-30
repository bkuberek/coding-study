pub fn find_target_sum_ways(nums: Vec<i32>, target: i32) -> i32 {
    let total: i32 = nums.iter().sum();
    if target.abs() > total {
        return 0;
    }
    let width = 2 * total as usize + 1;
    // ways[i][running + total] counts the sign assignments of nums[..i] with that running total.
    let mut ways = vec![vec![0; width]; nums.len() + 1];
    ways[0][total as usize] = 1;
    for (i, &value) in nums.iter().enumerate() {
        let value = value as usize;
        for offset in 0..width {
            let count = ways[i][offset];
            if count > 0 {
                // Only reachable offsets carry a count, and a reachable offset keeps both
                // offset + value and offset - value inside the table.
                ways[i + 1][offset + value] += count;
                ways[i + 1][offset - value] += count;
            }
        }
    }
    ways[nums.len()][(target + total) as usize]
}
