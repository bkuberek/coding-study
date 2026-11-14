/// Right, down, left, up: clockwise.
const DIRECTIONS: [(isize, isize); 4] = [(0, 1), (1, 0), (0, -1), (-1, 0)];

/// The cell one step from (r, c) along `heading`, or `None` outside the grid.
fn step(r: usize, c: usize, heading: usize, rows: usize, cols: usize) -> Option<(usize, usize)> {
    let (dr, dc) = DIRECTIONS[heading];
    let nr = r.checked_add_signed(dr)?;
    let nc = c.checked_add_signed(dc)?;
    (nr < rows && nc < cols).then_some((nr, nc))
}

pub fn spiral_order(matrix: Vec<Vec<i32>>) -> Vec<i32> {
    let (rows, cols) = (matrix.len(), matrix[0].len());
    let mut visited = vec![vec![false; cols]; rows];
    let mut order = Vec::with_capacity(rows * cols);
    let (mut r, mut c, mut heading) = (0, 0, 0);
    for _ in 0..rows * cols {
        order.push(matrix[r][c]);
        visited[r][c] = true;
        let ahead = step(r, c, heading, rows, cols).filter(|&(nr, nc)| !visited[nr][nc]);
        (r, c) = match ahead {
            Some(cell) => cell,
            None => {
                heading = (heading + 1) % 4;
                // Only after the last cell is there nowhere left to turn to; the loop ends anyway.
                step(r, c, heading, rows, cols).unwrap_or((r, c))
            }
        };
    }
    order
}
