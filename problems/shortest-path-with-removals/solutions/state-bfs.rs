use std::collections::VecDeque;

pub fn shortest_path(grid: Vec<Vec<i32>>, k: i32) -> i32 {
    let rows = grid.len();
    let cols = grid[0].len();
    // A Manhattan route enters at most rows + cols - 3 cells besides the corners, so more
    // removals than that never help.
    let budget = k.min((rows + cols).saturating_sub(3) as i32) as usize;
    let mut seen = vec![vec![vec![false; budget + 1]; cols]; rows];
    seen[0][0][0] = true;
    let mut queue = VecDeque::from([(0, 0, 0)]);
    let mut moves = 0;
    while !queue.is_empty() {
        for _ in 0..queue.len() {
            let (r, c, used) = queue.pop_front().unwrap();
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
                let after = used + grid[nr][nc] as usize;
                if after <= budget && !seen[nr][nc][after] {
                    seen[nr][nc][after] = true;
                    queue.push_back((nr, nc, after));
                }
            }
        }
        moves += 1;
    }
    -1
}
