use std::collections::HashSet;

const STEPS: [(isize, isize); 4] = [(1, 0), (-1, 0), (0, 1), (0, -1)];

fn count_islands(land: &[Vec<bool>], cells: &[(usize, usize)]) -> i32 {
    let (m, n) = (land.len(), land[0].len());
    let mut seen: HashSet<(usize, usize)> = HashSet::new();
    let mut islands = 0;
    for &start in cells {
        if seen.contains(&start) {
            continue;
        }
        islands += 1;
        seen.insert(start);
        let mut stack = vec![start];
        while let Some((r, c)) = stack.pop() {
            for (step_row, step_col) in STEPS {
                let (Some(nr), Some(nc)) = (
                    r.checked_add_signed(step_row),
                    c.checked_add_signed(step_col),
                ) else {
                    continue;
                };
                if nr < m && nc < n && land[nr][nc] && seen.insert((nr, nc)) {
                    stack.push((nr, nc));
                }
            }
        }
    }
    islands
}

pub fn num_islands2(m: i32, n: i32, positions: Vec<Vec<i32>>) -> Vec<i32> {
    let mut land = vec![vec![false; n as usize]; m as usize];
    let mut cells: Vec<(usize, usize)> = Vec::new(); // every land cell, each once
    let mut counts = Vec::with_capacity(positions.len());
    for position in &positions {
        let (r, c) = (position[0] as usize, position[1] as usize);
        if !land[r][c] {
            land[r][c] = true;
            cells.push((r, c));
        }
        counts.push(count_islands(&land, &cells));
    }
    counts
}
