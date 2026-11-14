use std::collections::VecDeque;

const STEPS: [(isize, isize); 4] = [(1, 0), (-1, 0), (0, 1), (0, -1)];

pub fn flood_fill(mut grid: Vec<Vec<i32>>, row: i32, col: i32, new_color: i32) -> Vec<Vec<i32>> {
    let (start_row, start_col) = (row as usize, col as usize);
    let old_color = grid[start_row][start_col];
    if old_color == new_color {
        return grid;
    }
    let size = (grid.len(), grid[0].len());
    grid[start_row][start_col] = new_color;
    let mut queue = VecDeque::from([(start_row, start_col)]);
    while let Some(cell) = queue.pop_front() {
        for step in STEPS {
            if let Some((nr, nc)) = neighbor(cell, step, size) {
                if grid[nr][nc] == old_color {
                    grid[nr][nc] = new_color;
                    queue.push_back((nr, nc));
                }
            }
        }
    }
    grid
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
