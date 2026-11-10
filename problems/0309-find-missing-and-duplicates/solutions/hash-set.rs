use std::collections::HashSet;

pub fn find_missing_and_duplicates(nums: Vec<i32>) -> Vec<Vec<i32>> {
    let mut seen = HashSet::new();
    let mut repeated = HashSet::new();
    for &value in &nums {
        if !seen.insert(value) {
            repeated.insert(value);
        }
    }
    // Walking 1..n instead of the sets keeps both answers sorted without a sort.
    let values = 1..=nums.len() as i32;
    let missing = values.clone().filter(|value| !seen.contains(value)).collect();
    let duplicated = values.filter(|value| repeated.contains(value)).collect();
    vec![missing, duplicated]
}
