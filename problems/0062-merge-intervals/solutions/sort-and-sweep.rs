pub fn merge(mut intervals: Vec<Vec<i32>>) -> Vec<Vec<i32>> {
    // `Vec<i32>` orders lexicographically, so this sorts by start, then end.
    intervals.sort();
    let mut merged: Vec<Vec<i32>> = Vec::new();
    for interval in intervals {
        let (start, end) = (interval[0], interval[1]);
        match merged.last_mut() {
            Some(last) if start <= last[1] => last[1] = last[1].max(end),
            _ => merged.push(vec![start, end]),
        }
    }
    merged
}
