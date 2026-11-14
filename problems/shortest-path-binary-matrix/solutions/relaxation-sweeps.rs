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
    let unreached = (n * n + 1) as i32;
    let mut dist = vec![vec![unreached; n]; n];
    dist[0][0] = 1;
    let mut order: Vec<(usize, usize)> = (0..n).flat_map(|r| (0..n).map(move |c| (r, c))).collect();
    let mut changed = true;
    while changed {
        changed = false;
        // Each sweep lets every open cell take the best distance offered by a neighbor.
        for &(r, c) in &order {
            if grid[r][c] == 1 {
                continue;
            }
            for (step_row, step_col) in STEPS {
                let (Some(nr), Some(nc)) = (
                    r.checked_add_signed(step_row),
                    c.checked_add_signed(step_col),
                ) else {
                    continue;
                };
                if nr < n && nc < n && dist[nr][nc] + 1 < dist[r][c] {
                    dist[r][c] = dist[nr][nc] + 1;
                    changed = true;
                }
            }
        }
        // Alternating the scan direction lets improvements travel both ways quickly.
        order.reverse();
    }
    let best = dist[n - 1][n - 1];
    if best < unreached {
        best
    } else {
        -1
    }
}
