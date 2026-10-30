pub fn employee_free_time(schedule: Vec<Vec<Vec<i32>>>) -> Vec<Vec<i32>> {
    let mut intervals: Vec<Vec<i32>> = schedule.into_iter().flatten().collect();
    intervals.sort_unstable();
    let mut free = Vec::new();
    let mut busy_until = intervals[0][1];
    for interval in &intervals {
        if interval[0] > busy_until {
            free.push(vec![busy_until, interval[0]]);
        }
        busy_until = busy_until.max(interval[1]);
    }
    free
}
