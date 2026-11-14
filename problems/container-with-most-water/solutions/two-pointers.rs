pub fn max_area(height: Vec<i32>) -> i32 {
    // `right` is one past the bar it stands for, so it never underflows on an empty input.
    let (mut left, mut right) = (0, height.len());
    let mut best = 0;
    while left + 1 < right {
        let width = (right - 1 - left) as i32;
        if height[left] < height[right - 1] {
            best = best.max(width * height[left]);
            left += 1;
        } else {
            best = best.max(width * height[right - 1]);
            right -= 1;
        }
    }
    best
}
