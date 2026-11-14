const STEPS: [(isize, isize); 4] = [(1, 0), (-1, 0), (0, 1), (0, -1)];

pub fn pacific_atlantic(heights: Vec<Vec<i32>>) -> Vec<Vec<i32>> {
    let size = (heights.len(), heights[0].len());
    // last_seen holds, for each cell, the id of the last search that visited it, so no array is
    // reallocated or cleared per search. Ids start at 1.
    let mut last_seen = vec![vec![0usize; size.1]; size.0];
    let mut result = Vec::new();
    for r in 0..size.0 {
        for c in 0..size.1 {
            let id = r * size.1 + c + 1;
            if drains_to_both(&heights, &mut last_seen, id, (r, c)) {
                result.push(vec![r as i32, c as i32]);
            }
        }
    }
    result
}

/// Follows the water downhill from `start` and reports whether it reaches both oceans.
fn drains_to_both(
    heights: &[Vec<i32>],
    last_seen: &mut [Vec<usize>],
    id: usize,
    start: (usize, usize),
) -> bool {
    let size = (heights.len(), heights[0].len());
    let (mut pacific, mut atlantic) = (false, false);
    last_seen[start.0][start.1] = id;
    let mut stack = vec![start];
    while let Some((r, c)) = stack.pop() {
        pacific = pacific || r == 0 || c == 0;
        atlantic = atlantic || r == size.0 - 1 || c == size.1 - 1;
        if pacific && atlantic {
            return true;
        }
        // Water runs to a neighbor that is not higher than the current cell.
        for step in STEPS {
            if let Some((nr, nc)) = neighbor((r, c), step, size) {
                if last_seen[nr][nc] != id && heights[nr][nc] <= heights[r][c] {
                    last_seen[nr][nc] = id;
                    stack.push((nr, nc));
                }
            }
        }
    }
    false
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
