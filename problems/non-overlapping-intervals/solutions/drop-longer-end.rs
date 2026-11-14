pub fn erase_overlap_intervals(mut intervals: Vec<Vec<i32>>) -> i32 {
    // `Vec<i32>` orders lexicographically, so this sorts by start, then end.
    intervals.sort();
    let mut removed = 0;
    let mut kept_end = intervals[0][1];
    for interval in &intervals[1..] {
        let (start, end) = (interval[0], interval[1]);
        if start < kept_end {
            // Conflict: keep whichever of the two ends first.
            removed += 1;
            kept_end = kept_end.min(end);
        } else {
            kept_end = end;
        }
    }
    removed
}
