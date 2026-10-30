pub fn can_partition(nums: Vec<i32>) -> bool {
    let total: i32 = nums.iter().sum();
    if total % 2 == 1 {
        return false;
    }
    let target = (total / 2) as usize;
    // reach[i][s] is true when some of the first i elements add up to exactly s.
    let mut reach = vec![vec![false; target + 1]; nums.len() + 1];
    reach[0][0] = true;
    for (i, &value) in nums.iter().enumerate() {
        let value = value as usize;
        // Rows i and i + 1 are borrowed at once: one to read, one to write.
        let (done, rest) = reach.split_at_mut(i + 1);
        let (previous, current) = (&done[i], &mut rest[0]);
        for s in 0..=target {
            current[s] = previous[s] || (s >= value && previous[s - value]);
        }
    }
    reach[nums.len()][target]
}
