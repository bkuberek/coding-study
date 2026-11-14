use std::cmp::Ordering;

pub fn three_sum(nums: Vec<i32>) -> Vec<Vec<i32>> {
    let mut values = nums;
    values.sort_unstable();
    let n = values.len();
    let mut triples = Vec::new();
    for i in 0..n.saturating_sub(2) {
        if values[i] > 0 {
            break;
        }
        if i > 0 && values[i] == values[i - 1] {
            continue;
        }
        let (mut left, mut right) = (i + 1, n - 1);
        while left < right {
            let total = values[i] + values[left] + values[right];
            match total.cmp(&0) {
                Ordering::Less => left += 1,
                Ordering::Greater => right -= 1,
                Ordering::Equal => {
                    triples.push(vec![values[i], values[left], values[right]]);
                    left += 1;
                    right -= 1;
                    while left < right && values[left] == values[left - 1] {
                        left += 1;
                    }
                }
            }
        }
    }
    triples
}
