pub fn can_attend_meetings(intervals: Vec<Vec<i32>>) -> bool {
    for (i, first) in intervals.iter().enumerate() {
        for second in &intervals[i + 1..] {
            // Half-open meetings share a moment exactly when each starts before the other ends.
            if first[0] < second[1] && second[0] < first[1] {
                return false;
            }
        }
    }
    true
}
