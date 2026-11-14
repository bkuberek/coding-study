use std::collections::VecDeque;

const LAND: char = '1';
const STEPS: [(isize, isize); 4] = [(1, 0), (-1, 0), (0, 1), (0, -1)];

pub fn num_islands(grid: Vec<Vec<char>>) -> i32 {
    let size = (grid.len(), grid[0].len());
    let mut visited = vec![vec![false; size.1]; size.0];
    let mut islands = 0;
    for row in 0..size.0 {
        for col in 0..size.1 {
            if grid[row][col] != LAND || visited[row][col] {
                continue;
            }
            islands += 1;
            visited[row][col] = true;
            let mut queue = VecDeque::from([(row, col)]);
            while let Some(cell) = queue.pop_front() {
                for step in STEPS {
                    if let Some((nr, nc)) = neighbor(cell, step, size) {
                        if grid[nr][nc] == LAND && !visited[nr][nc] {
                            visited[nr][nc] = true;
                            queue.push_back((nr, nc));
                        }
                    }
                }
            }
        }
    }
    islands
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
