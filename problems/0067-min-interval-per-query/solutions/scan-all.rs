pub fn min_interval(intervals: Vec<Vec<i32>>, queries: Vec<i32>) -> Vec<i32> {
    queries
        .iter()
        .map(|&query| {
            intervals
                .iter()
                .filter(|interval| interval[0] <= query && query <= interval[1])
                .map(|interval| interval[1] - interval[0] + 1)
                .min()
                .unwrap_or(-1)
        })
        .collect()
}
