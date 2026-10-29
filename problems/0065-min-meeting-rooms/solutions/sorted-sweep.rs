pub fn min_meeting_rooms(intervals: Vec<Vec<i32>>) -> i32 {
    let mut starts: Vec<i32> = intervals.iter().map(|interval| interval[0]).collect();
    let mut ends: Vec<i32> = intervals.iter().map(|interval| interval[1]).collect();
    starts.sort_unstable();
    ends.sort_unstable();
    let (mut rooms, mut ended) = (0, 0);
    for start in starts {
        if ends[ended] <= start {
            // Some meeting has ended by now: its room is reused.
            ended += 1;
        } else {
            rooms += 1;
        }
    }
    rooms
}
