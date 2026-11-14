pub fn latest_release(release_times: Vec<i64>, at: i64) -> i32 {
    // Half-open search space [lo, hi): every index below lo is a release at or before `at`, and
    // every index from hi on is a later one. Neither bound is ever decremented, so no usize
    // arithmetic can go below zero, not even for an empty list.
    let mut lo = 0;
    let mut hi = release_times.len();
    while lo < hi {
        let mid = lo + (hi - lo) / 2;
        if release_times[mid] <= at {
            lo = mid + 1;
        } else {
            hi = mid;
        }
    }
    lo as i32 - 1
}
