use std::cmp::Reverse;
use std::collections::BinaryHeap;

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
    // -1 marks a cell that is not settled yet.
    let mut removals = vec![vec![-1; cols]; rows];
    // `BinaryHeap` is a max-heap, so `Reverse` makes the cheapest entry pop first.
    // Entries are (removals so far, row, column); entering a cell costs its own value.
    let mut heap = BinaryHeap::new();
    heap.push(Reverse((0, 0, 0)));
    while let Some(Reverse((cost, r, c))) = heap.pop() {
        if removals[r][c] != -1 {
            continue; // an outdated entry: the cell was settled earlier at a lower cost
        }
        removals[r][c] = cost;
        if (r, c) == (rows - 1, cols - 1) {
            return cost;
        }
        for (nr, nc) in neighbors(r, c, rows, cols) {
            if removals[nr][nc] == -1 {
                heap.push(Reverse((cost + grid[nr][nc], nr, nc)));
            }
        }
    }
    unreachable!("the goal is always reachable when every obstacle may be removed")
}
