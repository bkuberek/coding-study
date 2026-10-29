use std::cmp::Ordering;

pub fn two_sum_sorted(numbers: Vec<i32>, target: i32) -> Vec<i32> {
    let (mut left, mut right) = (0, numbers.len().saturating_sub(1));
    while left < right {
        match (numbers[left] + numbers[right]).cmp(&target) {
            Ordering::Equal => return vec![left as i32, right as i32],
            Ordering::Less => left += 1,
            Ordering::Greater => right -= 1,
        }
    }
    vec![]
}
