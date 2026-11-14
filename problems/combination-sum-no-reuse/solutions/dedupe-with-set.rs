use std::collections::HashSet;

pub fn combination_sum2(candidates: Vec<i32>, target: i32) -> Vec<Vec<i32>> {
    let mut ordered = candidates;
    ordered.sort_unstable();
    // Values taken in sorted order give each multiset one canonical `Vec` to dedupe on.
    let found: HashSet<Vec<i32>> = (0..1u32 << ordered.len())
        .map(|mask| -> Vec<i32> {
            ordered
                .iter()
                .enumerate()
                .filter(|&(i, _)| (mask >> i) & 1 == 1)
                .map(|(_, &value)| value)
                .collect()
        })
        .filter(|chosen| chosen.iter().sum::<i32>() == target)
        .collect();
    found.into_iter().collect()
}
