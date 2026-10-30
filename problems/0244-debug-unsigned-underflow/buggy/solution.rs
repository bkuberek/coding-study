// Debug: Unsigned Underflow. Some tests fail: find the bug and fix it.
pub fn latest_release(release_times: Vec<i64>, at: i64) -> i32 {
    let mut lo = 0;
    let mut hi = release_times.len() - 1;
    let mut live = -1;
    while lo <= hi {
        let mid = lo + (hi - lo) / 2;
        if release_times[mid] <= at {
            live = mid as i32;
            lo = mid + 1;
        } else {
            hi = mid - 1;
        }
    }
    live
}
