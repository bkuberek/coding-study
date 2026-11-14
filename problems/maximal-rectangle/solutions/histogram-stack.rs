pub fn maximal_rectangle(matrix: Vec<Vec<char>>) -> i32 {
    // heights[c] counts the consecutive ones in column c ending at the current row.
    let mut heights = vec![0; matrix[0].len()];
    let mut best = 0;
    for row in &matrix {
        for (height, &cell) in heights.iter_mut().zip(row) {
            *height = if cell == '1' { *height + 1 } else { 0 };
        }
        best = best.max(largest_in_histogram(&heights));
    }
    best
}

fn largest_in_histogram(heights: &[i32]) -> i32 {
    let mut best = 0;
    // Indexes of bars whose heights strictly increase from bottom to top.
    let mut rising: Vec<usize> = Vec::with_capacity(heights.len() + 1);
    // One extra bar of height 0 at the end pops every bar still waiting.
    for index in 0..=heights.len() {
        let height = heights.get(index).copied().unwrap_or(0);
        while let Some(&top) = rising.last() {
            if heights[top] < height {
                break;
            }
            rising.pop();
            // The bar below on the stack bounds the rectangle on the left; with none, it
            // starts at column 0.
            let width = match rising.last() {
                Some(&left) => index - left - 1,
                None => index,
            };
            best = best.max(heights[top] * width as i32);
        }
        rising.push(index);
    }
    best
}
