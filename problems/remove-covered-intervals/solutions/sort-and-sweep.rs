pub fn remove_covered_intervals(intervals: Vec<Vec<i32>>) -> i32 {
    let mut ordered = intervals;
    // Equal starts: the longer interval comes first, so it covers the shorter ones after it.
    ordered.sort_unstable_by(|a, b| a[0].cmp(&b[0]).then(b[1].cmp(&a[1])));
    let mut remaining = 0;
    let mut reach = -1; // the largest end among the intervals already swept
    for interval in &ordered {
        if interval[1] > reach {
            remaining += 1;
            reach = interval[1];
        }
    }
    remaining
}
