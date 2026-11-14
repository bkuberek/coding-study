pub fn trap(height: Vec<i32>) -> i32 {
    let mut water = 0;
    for (i, &bar) in height.iter().enumerate() {
        // Each maximum scans a subslice: O(n) work per bar.
        let left = height[..=i].iter().copied().max().unwrap_or(0);
        let right = height[i..].iter().copied().max().unwrap_or(0);
        water += left.min(right) - bar;
    }
    water
}
