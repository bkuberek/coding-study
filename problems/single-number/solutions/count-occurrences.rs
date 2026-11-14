use std::collections::HashMap;

pub fn single_number(nums: Vec<i32>) -> i32 {
    let mut counts: HashMap<i32, i32> = HashMap::with_capacity(nums.len());
    for value in nums {
        *counts.entry(value).or_insert(0) += 1;
    }
    counts
        .into_iter()
        .find(|&(_, count)| count == 1)
        .map(|(value, _)| value)
        .expect("exactly one value occurs once")
}
