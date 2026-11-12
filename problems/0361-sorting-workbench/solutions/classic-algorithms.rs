use std::cmp::Reverse;
use std::collections::BinaryHeap;

/// Four classic sorts, each written the way the statement specifies it, with a meter that counts
/// the work of the latest sort. A sort returns a new vector and never changes its input.
pub struct SortingWorkbench {
    meter: Vec<i32>,
    merge_comparisons: i32,
}

impl SortingWorkbench {
    pub fn new() -> Self {
        SortingWorkbench { meter: Vec::new(), merge_comparisons: 0 }
    }

    // Level 1
    pub fn insertion_sort(&mut self, values: Vec<i32>) -> Vec<i32> {
        let mut items = values;
        let (mut comparisons, mut moves) = (0, 0);
        for i in 1..items.len() {
            let key = items[i];
            let mut j = i;
            while j > 0 {
                comparisons += 1;
                if items[j - 1] <= key {
                    break;
                }
                items[j] = items[j - 1];
                moves += 1;
                j -= 1;
            }
            items[j] = key;
        }
        self.meter = vec![comparisons, moves];
        items
    }

    pub fn report(&mut self) -> Vec<i32> {
        self.meter.clone()
    }

    // Level 2
    pub fn merge_sort_by(&mut self, rows: Vec<Vec<i32>>, key: i32) -> Vec<Vec<i32>> {
        self.merge_comparisons = 0;
        let merged = self.merge_sort(rows, key as usize);
        self.meter = vec![self.merge_comparisons];
        merged
    }

    fn merge_sort(&mut self, mut rows: Vec<Vec<i32>>, key: usize) -> Vec<Vec<i32>> {
        if rows.len() <= 1 {
            return rows;
        }
        let right_half = rows.split_off(rows.len() / 2);
        let left = self.merge_sort(rows, key);
        let right = self.merge_sort(right_half, key);
        let mut merged = Vec::with_capacity(left.len() + right.len());
        let (mut left, mut right) = (left.into_iter().peekable(), right.into_iter().peekable());
        while let (Some(front_left), Some(front_right)) = (left.peek(), right.peek()) {
            self.merge_comparisons += 1;
            if front_left[key] <= front_right[key] {
                merged.extend(left.next());
            } else {
                merged.extend(right.next());
            }
        }
        merged.extend(left);
        merged.extend(right);
        merged
    }

    // Level 3
    pub fn quick_sort(&mut self, values: Vec<i32>) -> Vec<i32> {
        let mut items = values;
        let (mut calls, mut steps) = (0, 0);
        let mut ranges = vec![(0_i32, items.len() as i32 - 1)];
        while let Some((low, high)) = ranges.pop() {
            if high - low < 1 {
                continue;
            }
            let (below, above) = partition(&mut items, low, high);
            calls += 1;
            steps += high - low + 1;
            ranges.push((low, below - 1));
            ranges.push((above + 1, high));
        }
        self.meter = vec![calls, steps];
        items
    }

    pub fn quick_select(&mut self, values: Vec<i32>, k: i32) -> i32 {
        let mut items = values;
        let target = k - 1;
        let (mut calls, mut steps) = (0, 0);
        let (mut low, mut high) = (0_i32, items.len() as i32 - 1);
        while low < high {
            let (below, above) = partition(&mut items, low, high);
            calls += 1;
            steps += high - low + 1;
            if target < below {
                high = below - 1;
            } else if target > above {
                low = above + 1;
            } else {
                break;
            }
        }
        self.meter = vec![calls, steps];
        items[target as usize]
    }

    // Level 4
    pub fn external_sort(&mut self, values: Vec<i32>, memory: i32, ways: i32) -> Vec<i32> {
        let mut runs: Vec<Vec<i32>> = values
            .chunks(memory as usize)
            .map(|chunk| {
                let mut run = chunk.to_vec();
                run.sort();
                run
            })
            .collect();
        let initial_runs = runs.len() as i32;
        let mut passes = 0;
        while runs.len() > 1 {
            runs = runs.chunks(ways as usize).map(merge_group).collect();
            passes += 1;
        }
        self.meter = vec![initial_runs, passes];
        runs.into_iter().next().unwrap_or_default()
    }
}

/// Returns (below, above): items[low..below] < pivot, items[below..=above] == pivot, the rest > pivot.
/// Positions are signed because `below - 1` is -1 when nothing is smaller than the pivot at index 0.
fn partition(items: &mut [i32], low: i32, high: i32) -> (i32, i32) {
    let pivot = items[(low + (high - low) / 2) as usize];
    let (mut below, mut i, mut above) = (low, low, high);
    while i <= above {
        let value = items[i as usize];
        if value < pivot {
            items.swap(below as usize, i as usize);
            below += 1;
            i += 1;
        } else if value > pivot {
            items.swap(i as usize, above as usize);
            above -= 1;
        } else {
            i += 1;
        }
    }
    (below, above)
}

/// A min-heap of (value, run, position in the run) holds the front value of each run.
fn merge_group(group: &[Vec<i32>]) -> Vec<i32> {
    let mut heap = BinaryHeap::new();
    for (index, run) in group.iter().enumerate() {
        heap.push(Reverse((run[0], index, 0_usize)));
    }
    let mut merged = Vec::with_capacity(group.iter().map(Vec::len).sum());
    while let Some(Reverse((value, index, position))) = heap.pop() {
        merged.push(value);
        if let Some(&next) = group[index].get(position + 1) {
            heap.push(Reverse((next, index, position + 1)));
        }
    }
    merged
}
