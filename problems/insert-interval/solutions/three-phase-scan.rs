pub fn insert(intervals: Vec<Vec<i32>>, new_interval: Vec<i32>) -> Vec<Vec<i32>> {
    let mut result = Vec::with_capacity(intervals.len() + 1);
    let (mut start, mut end) = (new_interval[0], new_interval[1]);
    let mut rest = intervals.into_iter().peekable();
    // Phase 1: intervals that end before the new one starts are copied unchanged.
    while let Some(interval) = rest.next_if(|interval| interval[1] < start) {
        result.push(interval);
    }
    // Phase 2: intervals that start by the time the new one ends are absorbed into it.
    while let Some(interval) = rest.next_if(|interval| interval[0] <= end) {
        start = start.min(interval[0]);
        end = end.max(interval[1]);
    }
    result.push(vec![start, end]);
    // Phase 3: everything after it is copied unchanged.
    result.extend(rest);
    result
}
