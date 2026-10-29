pub fn split_array(nums: Vec<i32>, k: i32) -> i32 {
    // Feasibility only improves as the limit grows: find the smallest feasible limit.
    let mut low = *nums.iter().max().unwrap();
    let mut high: i32 = nums.iter().sum();
    while low < high {
        let limit = low + (high - low) / 2;
        if pieces_needed(&nums, limit) <= k {
            high = limit;
        } else {
            low = limit + 1;
        }
    }
    low
}

/// Greedy: extend the current piece while it fits under the limit.
fn pieces_needed(nums: &[i32], limit: i32) -> i32 {
    let (mut pieces, mut running) = (1, 0);
    for &value in nums {
        if running + value > limit {
            pieces += 1;
            running = value;
        } else {
            running += value;
        }
    }
    pieces
}
