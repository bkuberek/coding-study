pub fn max_coins(nums: Vec<i32>) -> i32 {
    let mut values = Vec::with_capacity(nums.len() + 2);
    values.push(1);
    values.extend(nums);
    values.push(1);
    let size = values.len();
    // best[left][right]: most coins from bursting everything strictly between left and right.
    let mut best = vec![vec![0; size]; size];
    // An interval only depends on shorter ones, so fill by increasing gap right - left.
    for gap in 2..size {
        for left in 0..size - gap {
            let right = left + gap;
            let outer = values[left] * values[right];
            let mut top = 0;
            for last in left + 1..right {
                top = top.max(best[left][last] + outer * values[last] + best[last][right]);
            }
            best[left][right] = top;
        }
    }
    best[0][size - 1]
}
