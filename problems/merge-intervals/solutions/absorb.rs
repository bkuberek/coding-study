pub fn merge(intervals: Vec<Vec<i32>>) -> Vec<Vec<i32>> {
    let mut merged: Vec<Vec<i32>> = Vec::new();
    for interval in intervals {
        let (mut start, mut end) = (interval[0], interval[1]);
        // Fold every merged interval that shares a point with [start, end] into it.
        let mut separate = Vec::with_capacity(merged.len() + 1);
        for other in merged {
            if other[0] <= end && start <= other[1] {
                start = start.min(other[0]);
                end = end.max(other[1]);
            } else {
                separate.push(other);
            }
        }
        separate.push(vec![start, end]);
        merged = separate;
    }
    merged
}
