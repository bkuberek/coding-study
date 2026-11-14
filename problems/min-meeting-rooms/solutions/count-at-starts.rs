pub fn min_meeting_rooms(intervals: Vec<Vec<i32>>) -> i32 {
    // The busiest moment is always the start of some meeting.
    intervals
        .iter()
        .map(|moment| {
            intervals
                .iter()
                .filter(|other| other[0] <= moment[0] && moment[0] < other[1])
                .count()
        })
        .max()
        .unwrap_or(0) as i32
}
