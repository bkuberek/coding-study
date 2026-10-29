pub fn erase_overlap_intervals(mut intervals: Vec<Vec<i32>>) -> i32 {
    // `Vec<i32>` orders lexicographically, so this sorts by start, then end.
    intervals.sort();
    // longest[i]: the most intervals that can be kept among intervals[..=i], ending with intervals[i].
    let mut longest: Vec<usize> = Vec::with_capacity(intervals.len());
    for (i, interval) in intervals.iter().enumerate() {
        let best = (0..i)
            .filter(|&j| intervals[j][1] <= interval[0])
            .map(|j| longest[j])
            .max()
            .unwrap_or(0);
        longest.push(best + 1);
    }
    let most = longest.into_iter().max().unwrap_or(0);
    (intervals.len() - most) as i32
}
