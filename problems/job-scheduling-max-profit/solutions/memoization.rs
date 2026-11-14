pub fn job_scheduling(start_time: Vec<i32>, end_time: Vec<i32>, profit: Vec<i32>) -> i32 {
    // Each job is (start, end, profit), so sorting orders the jobs by start time.
    let mut jobs: Vec<(i32, i32, i32)> = (0..start_time.len())
        .map(|i| (start_time[i], end_time[i], profit[i]))
        .collect();
    jobs.sort();
    let starts: Vec<i32> = jobs.iter().map(|&(start, _, _)| start).collect();
    // memo[index] is the most profit from jobs[index..], or None while unknown.
    let mut memo = vec![None; jobs.len()];
    best_from(0, &jobs, &starts, &mut memo)
}

fn best_from(
    index: usize,
    jobs: &[(i32, i32, i32)],
    starts: &[i32],
    memo: &mut [Option<i32>],
) -> i32 {
    if index == jobs.len() {
        return 0;
    }
    if let Some(known) = memo[index] {
        return known;
    }
    let (_, end, pay) = jobs[index];
    // The first job after this one that starts once this one has ended.
    let following = index + 1 + starts[index + 1..].partition_point(|&start| start < end);
    let result = best_from(index + 1, jobs, starts, memo)
        .max(pay + best_from(following, jobs, starts, memo));
    memo[index] = Some(result);
    result
}
