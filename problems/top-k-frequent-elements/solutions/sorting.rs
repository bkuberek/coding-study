use std::collections::HashMap;

pub fn top_k_frequent(nums: Vec<i32>, k: i32) -> Vec<i32> {
    let mut counts: HashMap<i32, usize> = HashMap::new();
    for value in nums {
        *counts.entry(value).or_insert(0) += 1;
    }
    let mut by_count: Vec<(i32, usize)> = counts.into_iter().collect();
    by_count.sort_unstable_by_key(|&(_, count)| std::cmp::Reverse(count));
    by_count
        .into_iter()
        .take(k as usize)
        .map(|(value, _)| value)
        .collect()
}
