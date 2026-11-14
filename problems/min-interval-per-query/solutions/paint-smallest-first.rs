use std::collections::HashMap;

pub fn min_interval(mut intervals: Vec<Vec<i32>>, queries: Vec<i32>) -> Vec<i32> {
    let mut points = queries.clone();
    points.sort_unstable();
    points.dedup();
    let mut size_at = vec![-1; points.len()];
    // next_open[k]: a link toward the first point at or after k without an answer yet;
    // points.len() is a sentinel meaning "none left".
    let mut next_open: Vec<usize> = (0..=points.len()).collect();

    // `sort_by_key` is stable, like Python's `sorted`.
    intervals.sort_by_key(|interval| interval[1] - interval[0]);
    for interval in &intervals {
        let (left, right) = (interval[0], interval[1]);
        let mut k = first_open(
            &mut next_open,
            points.partition_point(|&point| point < left),
        );
        while k < points.len() && points[k] <= right {
            size_at[k] = right - left + 1;
            next_open[k] = k + 1;
            k = first_open(&mut next_open, k + 1);
        }
    }
    let position: HashMap<i32, usize> = points
        .iter()
        .enumerate()
        .map(|(k, &point)| (point, k))
        .collect();
    queries
        .iter()
        .map(|query| size_at[position[query]])
        .collect()
}

/// Finds the first point at or after `k` without an answer, compressing the path on the way.
fn first_open(next_open: &mut [usize], mut k: usize) -> usize {
    let mut root = k;
    while next_open[root] != root {
        root = next_open[root];
    }
    while next_open[k] != root {
        let following = next_open[k];
        next_open[k] = root;
        k = following;
    }
    root
}
