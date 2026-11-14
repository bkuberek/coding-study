pub fn erase_overlap_intervals(mut intervals: Vec<Vec<i32>>) -> i32 {
    // `sort_by_key` is stable, like Python's `sorted`.
    intervals.sort_by_key(|interval| interval[1]);
    let (mut kept, mut last_end) = (0, 0);
    for interval in &intervals {
        if kept == 0 || interval[0] >= last_end {
            kept += 1;
            last_end = interval[1];
        }
    }
    (intervals.len() - kept) as i32
}
