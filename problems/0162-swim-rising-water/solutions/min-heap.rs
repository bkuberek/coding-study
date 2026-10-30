use std::cmp::Reverse;
use std::collections::BinaryHeap;

const DIRECTIONS: [(isize, isize); 4] = [(1, 0), (-1, 0), (0, 1), (0, -1)];

pub fn swim_in_water(grid: Vec<Vec<i32>>) -> i32 {
    let n = grid.len();
    let mut seen = vec![vec![false; n]; n];
    seen[0][0] = true;
    // `BinaryHeap` is a max-heap, so `Reverse` makes the lowest level pop first.
    // Entries are (highest floor on the route so far, row, column).
    let mut heap = BinaryHeap::new();
    heap.push(Reverse((grid[0][0], 0, 0)));
    while let Some(Reverse((level, r, c))) = heap.pop() {
        if (r, c) == (n - 1, n - 1) {
            return level;
        }
        for (dr, dc) in DIRECTIONS {
            let (nr, nc) = (r as isize + dr, c as isize + dc);
            if nr < 0 || nc < 0 || nr >= n as isize || nc >= n as isize {
                continue;
            }
            let (nr, nc) = (nr as usize, nc as usize);
            if !seen[nr][nc] {
                seen[nr][nc] = true;
                heap.push(Reverse((level.max(grid[nr][nc]), nr, nc)));
            }
        }
    }
    unreachable!("the goal is always reachable once the water covers every floor")
}
