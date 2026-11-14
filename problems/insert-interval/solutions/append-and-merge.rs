pub fn insert(intervals: Vec<Vec<i32>>, new_interval: Vec<i32>) -> Vec<Vec<i32>> {
    let mut all = intervals;
    all.push(new_interval);
    // `Vec<i32>` orders lexicographically, so this sorts by start, then end.
    all.sort();
    let mut merged: Vec<Vec<i32>> = Vec::new();
    for interval in all {
        let (start, end) = (interval[0], interval[1]);
        match merged.last_mut() {
            Some(last) if start <= last[1] => last[1] = last[1].max(end),
            _ => merged.push(vec![start, end]),
        }
    }
    merged
}
