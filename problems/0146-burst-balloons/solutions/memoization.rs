pub fn max_coins(nums: Vec<i32>) -> i32 {
    // Pad with the virtual balloons of value 1 at both ends.
    let mut values = Vec::with_capacity(nums.len() + 2);
    values.push(1);
    values.extend(nums);
    values.push(1);
    // best[left][right] caches the most coins from bursting every balloon strictly between
    // left and right, while those two are still standing; None is unknown.
    let mut best = vec![vec![None; values.len()]; values.len()];
    solve(0, values.len() - 1, &values, &mut best)
}

fn solve(left: usize, right: usize, values: &[i32], best: &mut [Vec<Option<i32>>]) -> i32 {
    if right - left < 2 {
        return 0;
    }
    if let Some(known) = best[left][right] {
        return known;
    }
    // Choose the balloon `last` that is burst last between them: its neighbors are then
    // exactly left and right, and the two sides are independent.
    let mut top = 0;
    for last in left + 1..right {
        let coins = solve(left, last, values, best)
            + values[left] * values[last] * values[right]
            + solve(last, right, values, best);
        top = top.max(coins);
    }
    best[left][right] = Some(top);
    top
}
