pub fn max_area(height: Vec<i32>) -> i32 {
    let mut best = 0;
    for left in 0..height.len().saturating_sub(1) {
        for right in left + 1..height.len() {
            let water = (right - left) as i32 * height[left].min(height[right]);
            best = best.max(water);
        }
    }
    best
}
