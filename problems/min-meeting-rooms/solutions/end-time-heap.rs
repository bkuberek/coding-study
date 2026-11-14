use std::cmp::Reverse;
use std::collections::BinaryHeap;

pub fn min_meeting_rooms(mut intervals: Vec<Vec<i32>>) -> i32 {
    // `Vec<i32>` orders lexicographically, so this sorts by start, then end.
    intervals.sort();
    // End times of the meetings currently holding a room; `Reverse` makes the max-heap pop the
    // smallest first.
    let mut ends: BinaryHeap<Reverse<i32>> = BinaryHeap::new();
    for interval in intervals {
        let (start, end) = (interval[0], interval[1]);
        match ends.peek() {
            // Some meeting has ended by now: replace its end time with the new one.
            Some(&Reverse(earliest)) if earliest <= start => {
                ends.pop();
                ends.push(Reverse(end));
            }
            _ => ends.push(Reverse(end)),
        }
    }
    ends.len() as i32
}
