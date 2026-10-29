pub fn largest_rectangle_area(heights: Vec<i32>) -> i32 {
    let mut best = 0;
    for (left, &first) in heights.iter().enumerate() {
        // The tallest rectangle spanning bars left..right is as high as the lowest of them.
        let mut lowest = first;
        for (offset, &height) in heights[left..].iter().enumerate() {
            lowest = lowest.min(height);
            best = best.max(lowest * (offset as i32 + 1));
        }
    }
    best
}
