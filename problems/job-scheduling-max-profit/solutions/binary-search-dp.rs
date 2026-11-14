pub fn job_scheduling(start_time: Vec<i32>, end_time: Vec<i32>, profit: Vec<i32>) -> i32 {
    // Each job is (end, start, profit), so sorting orders the jobs by end time.
    let mut jobs: Vec<(i32, i32, i32)> = (0..start_time.len())
        .map(|i| (end_time[i], start_time[i], profit[i]))
        .collect();
    jobs.sort();
    let ends: Vec<i32> = jobs.iter().map(|&(end, _, _)| end).collect();
    // best[i] is the most profit from the first i jobs in end-time order.
    let mut best = vec![0; jobs.len() + 1];
    for (i, &(_, start, pay)) in jobs.iter().enumerate() {
        // The number of jobs that end no later than this one starts (all of them come
        // first): the ends are sorted, so partition_point finds the boundary.
        let compatible = ends[..i].partition_point(|&end| end <= start);
        best[i + 1] = best[i].max(pay + best[compatible]);
    }
    best[jobs.len()]
}
