pub fn can_attend_meetings(intervals: Vec<Vec<i32>>) -> bool {
    let mut ordered = intervals;
    ordered.sort_unstable_by_key(|meeting| meeting[0]);
    // After sorting by start, only neighbors can be the first clash.
    ordered.windows(2).all(|pair| pair[0][1] <= pair[1][0])
}
