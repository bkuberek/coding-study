const LAND: char = '1';
const WATER: char = '0';
const STEPS: [(isize, isize); 4] = [(1, 0), (-1, 0), (0, 1), (0, -1)];

pub fn num_islands(mut grid: Vec<Vec<char>>) -> i32 {
    let size = (grid.len(), grid[0].len());
    let mut islands = 0;
    for row in 0..size.0 {
        for col in 0..size.1 {
            if grid[row][col] != LAND {
                continue;
            }
            islands += 1;
            // Sink the island: every land square becomes water as soon as it is discovered,
            // so it is pushed at most once and never counted again.
            grid[row][col] = WATER;
            let mut stack = vec![(row, col)];
            while let Some(cell) = stack.pop() {
                for step in STEPS {
                    if let Some((nr, nc)) = neighbor(cell, step, size) {
                        if grid[nr][nc] == LAND {
                            grid[nr][nc] = WATER;
                            stack.push((nr, nc));
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
