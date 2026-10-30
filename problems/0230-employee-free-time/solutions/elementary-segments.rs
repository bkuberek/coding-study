pub fn employee_free_time(schedule: Vec<Vec<Vec<i32>>>) -> Vec<Vec<i32>> {
    let intervals: Vec<&Vec<i32>> = schedule.iter().flatten().collect();
    let mut points: Vec<i32> = intervals
        .iter()
        .flat_map(|interval| interval.iter().copied())
        .collect();
    points.sort_unstable();
    points.dedup();

    let mut free = Vec::new();
    for pair in points.windows(2) {
        let (left, right) = (pair[0], pair[1]);
        // No interval starts or ends strictly inside (left, right): it is all busy or all free.
        let busy = intervals
            .iter()
            .any(|interval| interval[0] <= left && left < interval[1]);
        if !busy {
            free.push(vec![left, right]);
        }
    }
    free
}
