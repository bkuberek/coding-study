const STEPS: [(isize, isize); 4] = [(1, 0), (-1, 0), (0, 1), (0, -1)];

// The cells next to (r, c) that lie inside a grid of the given size.
fn neighbors(
    r: usize,
    c: usize,
    rows: usize,
    columns: usize,
) -> impl Iterator<Item = (usize, usize)> {
    STEPS.into_iter().filter_map(move |(dr, dc)| {
        let nr = r.checked_add_signed(dr)?;
        let nc = c.checked_add_signed(dc)?;
        (nr < rows && nc < columns).then_some((nr, nc))
    })
}

pub fn longest_increasing_path(matrix: Vec<Vec<i32>>) -> i32 {
    let (rows, columns) = (matrix.len(), matrix[0].len());
    // larger[r][c] counts the neighbors a path could still step up to from (r, c).
    let mut larger = vec![vec![0u8; columns]; rows];
    let mut layer = Vec::new();
    for r in 0..rows {
        for c in 0..columns {
            larger[r][c] = neighbors(r, c, rows, columns)
                .filter(|&(nr, nc)| matrix[nr][nc] > matrix[r][c])
                .count() as u8;
            if larger[r][c] == 0 {
                layer.push((r, c));
            }
        }
    }
    // Kahn's algorithm from the sinks: each round removes the cells whose larger neighbors are
    // all gone. A cell removed in round k starts a longest path of exactly k cells.
    let mut rounds = 0;
    while !layer.is_empty() {
        rounds += 1;
        let mut next_layer = Vec::new();
        for (r, c) in layer {
            for (nr, nc) in neighbors(r, c, rows, columns) {
                if matrix[nr][nc] < matrix[r][c] {
                    larger[nr][nc] -= 1;
                    if larger[nr][nc] == 0 {
                        next_layer.push((nr, nc));
                    }
                }
            }
        }
        layer = next_layer;
    }
    rounds
}
