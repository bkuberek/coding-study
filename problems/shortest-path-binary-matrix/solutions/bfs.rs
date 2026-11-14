use std::collections::VecDeque;

const STEPS: [(isize, isize); 8] = [
    (-1, -1),
    (-1, 0),
    (-1, 1),
    (0, -1),
    (0, 1),
    (1, -1),
    (1, 0),
    (1, 1),
];

pub fn shortest_path_binary_matrix(grid: Vec<Vec<i32>>) -> i32 {
    let n = grid.len();
    if grid[0][0] == 1 || grid[n - 1][n - 1] == 1 {
        return -1;
    }
    let mut dist = vec![vec![0; n]; n];
    dist[0][0] = 1;
    let mut queue = VecDeque::from([(0, 0)]);
    while let Some((r, c)) = queue.pop_front() {
        if (r, c) == (n - 1, n - 1) {
            return dist[r][c];
        }
        for (step_row, step_col) in STEPS {
            let (Some(nr), Some(nc)) = (
                r.checked_add_signed(step_row),
                c.checked_add_signed(step_col),
            ) else {
                continue;
            };
            // dist 0 means "not reached yet": every reached cell has length at least 1.
            if nr < n && nc < n && grid[nr][nc] == 0 && dist[nr][nc] == 0 {
                dist[nr][nc] = dist[r][c] + 1;
                queue.push_back((nr, nc));
            }
        }
    }
    -1
}
