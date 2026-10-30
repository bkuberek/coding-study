use std::collections::VecDeque;

const DIRECTIONS: [(isize, isize); 4] = [(1, 0), (-1, 0), (0, 1), (0, -1)];

/// The cells next to (r, c) that lie inside the grid.
fn neighbors(r: usize, c: usize, rows: usize, cols: usize) -> impl Iterator<Item = (usize, usize)> {
    DIRECTIONS.into_iter().filter_map(move |(dr, dc)| {
        let nr = r.checked_add_signed(dr)?;
        let nc = c.checked_add_signed(dc)?;
        (nr < rows && nc < cols).then_some((nr, nc))
    })
}

pub fn minimum_obstacles(grid: Vec<Vec<i32>>) -> i32 {
    let (rows, cols) = (grid.len(), grid[0].len());
    let unreached = (rows * cols) as i32;
    let mut removals = vec![vec![unreached; cols]; rows];
    removals[0][0] = 0;
    // The deque stays sorted by removals: zero-cost steps go to the front, one-cost steps
    // to the back, so its two ends never differ by more than one.
    let mut queue = VecDeque::from([(0, 0)]);
    while let Some((r, c)) = queue.pop_front() {
        let cost = removals[r][c];
        if (r, c) == (rows - 1, cols - 1) {
            return cost;
        }
        for (nr, nc) in neighbors(r, c, rows, cols) {
            if cost + grid[nr][nc] < removals[nr][nc] {
                removals[nr][nc] = cost + grid[nr][nc];
                if grid[nr][nc] == 0 {
                    queue.push_front((nr, nc));
                } else {
                    queue.push_back((nr, nc));
                }
            }
        }
    }
    removals[rows - 1][cols - 1]
}
