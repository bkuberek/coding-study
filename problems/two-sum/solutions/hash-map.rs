use std::collections::HashMap;

pub fn two_sum(nums: Vec<i32>, target: i32) -> Vec<i32> {
    let mut index_by_value = HashMap::with_capacity(nums.len());
    for (i, &value) in nums.iter().enumerate() {
        if let Some(&partner) = index_by_value.get(&(target - value)) {
            return vec![partner as i32, i as i32];
        }
        index_by_value.insert(value, i);
    }
    vec![]
}
