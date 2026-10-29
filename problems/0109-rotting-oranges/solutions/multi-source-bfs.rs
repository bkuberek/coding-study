use std::collections::VecDeque;

const FRESH: i32 = 1;
const ROTTEN: i32 = 2;

pub fn oranges_rotting(mut grid: Vec<Vec<i32>>) -> i32 {
    let rows = grid.len();
    let cols = grid[0].len();
    let mut queue = VecDeque::new();
    let mut fresh = 0;
    for (r, row) in grid.iter().enumerate() {
        for (c, &cell) in row.iter().enumerate() {
            if cell == ROTTEN {
                queue.push_back((r, c));
            } else if cell == FRESH {
                fresh += 1;
            }
        }
    }
    let mut minutes = 0;
    // Each pass of the outer loop is one minute: it rots the whole current frontier.
    while !queue.is_empty() && fresh > 0 {
        minutes += 1;
        for _ in 0..queue.len() {
            let (r, c) = queue.pop_front().unwrap();
            for (step_row, step_col) in [(1isize, 0isize), (-1, 0), (0, 1), (0, -1)] {
                let (Some(nr), Some(nc)) = (
                    r.checked_add_signed(step_row),
                    c.checked_add_signed(step_col),
                ) else {
                    continue;
                };
                if nr < rows && nc < cols && grid[nr][nc] == FRESH {
                    grid[nr][nc] = ROTTEN;
                    fresh -= 1;
                    queue.push_back((nr, nc));
                }
            }
        }
    }
    if fresh == 0 {
        minutes
    } else {
        -1
    }
}
