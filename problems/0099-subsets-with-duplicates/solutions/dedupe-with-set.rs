use std::collections::HashSet;

pub fn subsets_with_dup(nums: Vec<i32>) -> Vec<Vec<i32>> {
    let mut ordered = nums;
    ordered.sort_unstable();
    // Taking values in sorted order gives every multiset one canonical `Vec` to dedupe on.
    let distinct: HashSet<Vec<i32>> = (0..1u32 << ordered.len())
        .map(|mask| {
            ordered
                .iter()
                .enumerate()
                .filter(|&(i, _)| (mask >> i) & 1 == 1)
                .map(|(_, &value)| value)
                .collect()
        })
        .collect();
    distinct.into_iter().collect()
}
