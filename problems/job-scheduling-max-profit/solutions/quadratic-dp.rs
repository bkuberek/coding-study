pub fn job_scheduling(start_time: Vec<i32>, end_time: Vec<i32>, profit: Vec<i32>) -> i32 {
    // Each job is (end, start, profit), so sorting orders the jobs by end time.
    let mut jobs: Vec<(i32, i32, i32)> = (0..start_time.len())
        .map(|i| (end_time[i], start_time[i], profit[i]))
        .collect();
    jobs.sort();
    // best[i] is the most profit from the first i jobs in end-time order.
    let mut best = vec![0; jobs.len() + 1];
    for (i, &(_, start, pay)) in jobs.iter().enumerate() {
        // Walk back to the last job that ends no later than this one starts.
        let mut compatible = i;
        while compatible > 0 && jobs[compatible - 1].0 > start {
            compatible -= 1;
        }
        best[i + 1] = best[i].max(pay + best[compatible]);
    }
    best[jobs.len()]
}
