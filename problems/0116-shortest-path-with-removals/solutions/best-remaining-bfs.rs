use std::collections::VecDeque;

pub fn shortest_path(grid: Vec<Vec<i32>>, k: i32) -> i32 {
    let rows = grid.len();
    let cols = grid[0].len();
    let span = (rows + cols) as i32;
    let shortest = span - 2;
    // Enough removals for the straight Manhattan route: nothing can beat it.
    if k >= span - 3 {
        return shortest;
    }
    // best[r][c] is the most removals left with which (r, c) was reached so far.
    let mut best = vec![vec![-1; cols]; rows];
    best[0][0] = k;
    let mut queue = VecDeque::from([(0, 0, k)]);
    let mut moves = 0;
    while !queue.is_empty() {
        for _ in 0..queue.len() {
            let (r, c, left) = queue.pop_front().unwrap();
            if (r, c) == (rows - 1, cols - 1) {
                return moves;
            }
            for (step_row, step_col) in [(1isize, 0isize), (-1, 0), (0, 1), (0, -1)] {
                let (Some(nr), Some(nc)) = (
                    r.checked_add_signed(step_row),
                    c.checked_add_signed(step_col),
                ) else {
                    continue;
                };
                if nr >= rows || nc >= cols {
                    continue;
                }
                let remaining = left - grid[nr][nc];
                // A visit that arrives later with no more removals left can never do better.
                if remaining > best[nr][nc] {
                    best[nr][nc] = remaining;
                    queue.push_back((nr, nc, remaining));
                }
            }
        }
        moves += 1;
    }
    -1
}
