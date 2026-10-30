const STEPS: [(isize, isize); 4] = [(1, 0), (-1, 0), (0, 1), (0, -1)];

fn find(parent: &[usize], mut x: usize) -> usize {
    while parent[x] != x {
        x = parent[x];
    }
    x
}

pub fn num_islands2(m: i32, n: i32, positions: Vec<Vec<i32>>) -> Vec<i32> {
    let (m, n) = (m as usize, n as usize);
    let mut parent: Vec<usize> = (0..m * n).collect(); // cell r * n + c; parent[x] == x marks a root
    let mut land = vec![false; m * n];

    let mut islands = 0;
    let mut counts = Vec::with_capacity(positions.len());
    for position in &positions {
        let (r, c) = (position[0] as usize, position[1] as usize);
        let cell = r * n + c;
        if !land[cell] {
            land[cell] = true;
            islands += 1; // a new island, until it merges with its neighbors
            for (step_row, step_col) in STEPS {
                let (Some(nr), Some(nc)) = (
                    r.checked_add_signed(step_row),
                    c.checked_add_signed(step_col),
                ) else {
                    continue;
                };
                if nr < m && nc < n && land[nr * n + nc] {
                    let (root_neighbor, root_cell) =
                        (find(&parent, nr * n + nc), find(&parent, cell));
                    if root_neighbor != root_cell {
                        parent[root_neighbor] = root_cell; // no balancing: chains can grow
                        islands -= 1;
                    }
                }
            }
        }
        counts.push(islands);
    }
    counts
}
