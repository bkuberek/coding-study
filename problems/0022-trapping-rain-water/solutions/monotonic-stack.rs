pub fn trap(height: Vec<i32>) -> i32 {
    let mut water = 0;
    let mut falling: Vec<usize> = Vec::new(); // indexes of bars with non-increasing heights
    for (right, &bar) in height.iter().enumerate() {
        while let Some(&top) = falling.last() {
            if height[top] >= bar {
                break;
            }
            falling.pop();
            let bottom = height[top];
            let Some(&left) = falling.last() else {
                break;
            };
            let level = height[left].min(bar);
            water += (right - left - 1) as i32 * (level - bottom);
        }
        falling.push(right);
    }
    water
}
