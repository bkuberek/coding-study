pub fn largest_rectangle_area(heights: Vec<i32>) -> i32 {
    let mut best = 0;
    // Indexes of bars whose heights strictly increase from bottom to top.
    let mut rising: Vec<usize> = Vec::new();
    // One extra bar of height 0 at the end pops every bar still waiting.
    for index in 0..=heights.len() {
        let height = heights.get(index).copied().unwrap_or(0);
        while let Some(&top) = rising.last() {
            if heights[top] < height {
                break;
            }
            rising.pop();
            // The bar below `top` on the stack is lower, and so is `index` (or it is equal and a
            // later pop covers the full width): the rectangle spans the bars between them.
            let first = rising.last().map_or(0, |&below| below + 1);
            best = best.max(heights[top] * (index - first) as i32);
        }
        rising.push(index);
    }
    best
}
