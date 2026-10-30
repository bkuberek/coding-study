pub fn find_target_sum_ways(nums: Vec<i32>, target: i32) -> i32 {
    let total: i32 = nums.iter().sum();
    // With P the plus part: P - (total - P) = target, so P = (total + target) / 2.
    if target.abs() > total || (total + target) % 2 != 0 {
        return 0;
    }
    let plus = ((total + target) / 2) as usize;
    // ways[p] counts the subsets of the values seen so far that add up to p.
    let mut ways = vec![0; plus + 1];
    ways[0] = 1;
    for &value in &nums {
        let value = value as usize;
        // Decreasing p: ways[p - value] still excludes this value, so it is used at most once.
        for p in (value..=plus).rev() {
            ways[p] += ways[p - value];
        }
    }
    ways[plus]
}
