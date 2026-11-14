use std::collections::VecDeque;

const STEPS: [(isize, isize); 4] = [(1, 0), (-1, 0), (0, 1), (0, -1)];

/// The cells whose water can reach a coast: searches uphill from all the coast cells at once.
fn climb(heights: &[Vec<i32>], coast: &[(usize, usize)]) -> Vec<Vec<bool>> {
    let size = (heights.len(), heights[0].len());
    let mut reached = vec![vec![false; size.1]; size.0];
    let mut queue = VecDeque::new();
    for &(r, c) in coast {
        // The corner shared by two sides of the coast is listed twice; enqueue it once.
        if !reached[r][c] {
            reached[r][c] = true;
            queue.push_back((r, c));
        }
    }
    while let Some((r, c)) = queue.pop_front() {
        for step in STEPS {
            if let Some((nr, nc)) = neighbor((r, c), step, size) {
                if !reached[nr][nc] && heights[nr][nc] >= heights[r][c] {
                    reached[nr][nc] = true;
                    queue.push_back((nr, nc));
                }
            }
        }
    }
    reached
}

pub fn pacific_atlantic(heights: Vec<Vec<i32>>) -> Vec<Vec<i32>> {
    let (rows, cols) = (heights.len(), heights[0].len());
    let pacific_coast: Vec<(usize, usize)> = (0..cols)
        .map(|c| (0, c))
        .chain((0..rows).map(|r| (r, 0)))
        .collect();
    let atlantic_coast: Vec<(usize, usize)> = (0..cols)
        .map(|c| (rows - 1, c))
        .chain((0..rows).map(|r| (r, cols - 1)))
        .collect();
    let pacific = climb(&heights, &pacific_coast);
    let atlantic = climb(&heights, &atlantic_coast);
    let mut result = Vec::new();
    for r in 0..rows {
        for c in 0..cols {
            if pacific[r][c] && atlantic[r][c] {
                result.push(vec![r as i32, c as i32]);
            }
        }
    }
    result
}

/// The cell one `step` away, or `None` when it falls off a grid of `size` (rows, columns).
fn neighbor(
    cell: (usize, usize),
    step: (isize, isize),
    size: (usize, usize),
) -> Option<(usize, usize)> {
    let row = cell.0.checked_add_signed(step.0)?;
    let col = cell.1.checked_add_signed(step.1)?;
    (row < size.0 && col < size.1).then_some((row, col))
}
