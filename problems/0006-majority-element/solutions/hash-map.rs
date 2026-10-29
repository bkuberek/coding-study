use std::collections::HashMap;

pub fn majority_element(nums: Vec<i32>) -> i32 {
    let half = nums.len() / 2;
    let mut counts: HashMap<i32, usize> = HashMap::with_capacity(nums.len());
    for value in nums {
        let count = counts.entry(value).or_insert(0);
        *count += 1;
        if *count > half {
            return value;
        }
    }
    panic!("no majority element");
}
