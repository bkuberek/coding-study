pub fn trap(height: Vec<i32>) -> i32 {
    let running_max = |tallest: &mut i32, &bar: &i32| {
        *tallest = (*tallest).max(bar);
        Some(*tallest)
    };
    // left_max[i] is the tallest bar in height[..=i].
    let left_max: Vec<i32> = height.iter().scan(0, running_max).collect();
    // right_max[i] is the tallest bar in height[i..], built from the right and flipped.
    let mut right_max: Vec<i32> = height.iter().rev().scan(0, running_max).collect();
    right_max.reverse();
    left_max
        .iter()
        .zip(&right_max)
        .zip(&height)
        .map(|((&left, &right), &bar)| left.min(right) - bar)
        .sum()
}
