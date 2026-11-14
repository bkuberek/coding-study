use std::collections::VecDeque;

const DIRECTIONS: [(isize, isize); 4] = [(1, 0), (-1, 0), (0, 1), (0, -1)];

/// Can the goal be reached when the water stands at `time`?
fn reachable(grid: &[Vec<i32>], time: i32) -> bool {
    let n = grid.len();
    if grid[0][0] > time {
        return false;
    }
    let mut seen = vec![vec![false; n]; n];
    seen[0][0] = true;
    let mut queue = VecDeque::from([(0, 0)]);
    while let Some((r, c)) = queue.pop_front() {
        if (r, c) == (n - 1, n - 1) {
            return true;
        }
        for (dr, dc) in DIRECTIONS {
            let (nr, nc) = (r as isize + dr, c as isize + dc);
            if nr < 0 || nc < 0 || nr >= n as isize || nc >= n as isize {
                continue;
            }
            let (nr, nc) = (nr as usize, nc as usize);
            if !seen[nr][nc] && grid[nr][nc] <= time {
                seen[nr][nc] = true;
                queue.push_back((nr, nc));
            }
        }
    }
    false
}

pub fn swim_in_water(grid: Vec<Vec<i32>>) -> i32 {
    let n = grid.len() as i32;
    // The answer is at least both corner heights and at most the highest floor.
    let mut low = grid[0][0].max(grid[n as usize - 1][n as usize - 1]);
    let mut high = n * n - 1;
    while low < high {
        let middle = (low + high) / 2;
        if reachable(&grid, middle) {
            high = middle;
        } else {
            low = middle + 1;
        }
    }
    low
}
