use std::collections::HashSet;

pub fn three_sum(nums: Vec<i32>) -> Vec<Vec<i32>> {
    let mut values = nums;
    values.sort_unstable();
    let mut triples = Vec::new();
    for i in 0..values.len().saturating_sub(2) {
        if i > 0 && values[i] == values[i - 1] {
            continue;
        }
        let mut seen = HashSet::new();
        let mut last_largest = None;
        for j in i + 1..values.len() {
            let middle = -values[i] - values[j];
            if seen.contains(&middle) && last_largest != Some(values[j]) {
                triples.push(vec![values[i], middle, values[j]]);
                last_largest = Some(values[j]);
            }
            seen.insert(values[j]);
        }
    }
    triples
}
