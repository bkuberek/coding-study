pub fn remove_covered_intervals(intervals: Vec<Vec<i32>>) -> i32 {
    let mut remaining = 0;
    for (i, interval) in intervals.iter().enumerate() {
        let covered = intervals
            .iter()
            .enumerate()
            .any(|(j, other)| j != i && other[0] <= interval[0] && interval[1] <= other[1]);
        if !covered {
            remaining += 1;
        }
    }
    remaining
}
