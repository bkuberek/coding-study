pub fn num_of_minutes(n: i32, head_id: i32, manager: Vec<i32>, inform_time: Vec<i32>) -> i32 {
    let mut reports: Vec<Vec<usize>> = vec![Vec::new(); n as usize];
    for (employee, &boss) in manager.iter().enumerate() {
        if boss != -1 {
            reports[boss as usize].push(employee);
        }
    }
    let mut longest = 0;
    // (employee, minute at which they hear the news)
    let mut pending = vec![(head_id as usize, 0)];
    while let Some((employee, heard_at)) = pending.pop() {
        longest = longest.max(heard_at);
        let passed_on_at = heard_at + inform_time[employee];
        pending.extend(
            reports[employee]
                .iter()
                .map(|&report| (report, passed_on_at)),
        );
    }
    longest
}
