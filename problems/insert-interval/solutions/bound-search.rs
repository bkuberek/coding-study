pub fn insert(intervals: Vec<Vec<i32>>, new_interval: Vec<i32>) -> Vec<Vec<i32>> {
    let (mut start, mut end) = (new_interval[0], new_interval[1]);
    // Separate sorted intervals have increasing starts and increasing ends, so both bounds
    // are binary searches: `partition_point` returns the first index where the predicate fails.
    let first = intervals.partition_point(|interval| interval[1] < start);
    let after = intervals.partition_point(|interval| interval[0] <= end);
    if first < after {
        start = start.min(intervals[first][0]);
        end = end.max(intervals[after - 1][1]);
    }
    let mut result = intervals;
    let suffix = result.split_off(after);
    result.truncate(first);
    result.push(vec![start, end]);
    result.extend(suffix);
    result
}
