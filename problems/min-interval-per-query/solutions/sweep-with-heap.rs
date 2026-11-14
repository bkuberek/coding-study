use std::cmp::Reverse;
use std::collections::BinaryHeap;

pub fn min_interval(mut intervals: Vec<Vec<i32>>, queries: Vec<i32>) -> Vec<i32> {
    // `Vec<i32>` orders lexicographically, so this sorts by left end, then right end.
    intervals.sort();
    let mut answer = vec![-1; queries.len()];
    // Entries are (size, right) of intervals that start at or before the current query; the
    // `Reverse` wrapper turns the max-heap into a min-heap.
    let mut candidates: BinaryHeap<Reverse<(i32, i32)>> = BinaryHeap::new();
    let mut added = 0;
    let mut order: Vec<usize> = (0..queries.len()).collect();
    order.sort_by_key(|&index| queries[index]);
    for index in order {
        let query = queries[index];
        while added < intervals.len() && intervals[added][0] <= query {
            let (left, right) = (intervals[added][0], intervals[added][1]);
            candidates.push(Reverse((right - left + 1, right)));
            added += 1;
        }
        // An interval that ends before this query also ends before every later one.
        while candidates
            .peek()
            .is_some_and(|&Reverse((_, right))| right < query)
        {
            candidates.pop();
        }
        if let Some(&Reverse((size, _))) = candidates.peek() {
            answer[index] = size;
        }
    }
    answer
}
