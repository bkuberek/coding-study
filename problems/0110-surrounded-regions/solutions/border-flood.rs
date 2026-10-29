const SAFE: char = 'S';

#[allow(clippy::ptr_arg)] // the signature is fixed: the board is changed in place
pub fn solve(board: &mut Vec<Vec<char>>) {
    let rows = board.len();
    let cols = board[0].len();
    // Every 'O' on the edge is safe; so is everything connected to one of them.
    let mut stack = Vec::new();
    for (r, row) in board.iter_mut().enumerate() {
        for (c, cell) in row.iter_mut().enumerate() {
            let on_edge = r == 0 || r == rows - 1 || c == 0 || c == cols - 1;
            if on_edge && *cell == 'O' {
                *cell = SAFE;
                stack.push((r, c));
            }
        }
    }
    while let Some((r, c)) = stack.pop() {
        for (step_row, step_col) in [(1isize, 0isize), (-1, 0), (0, 1), (0, -1)] {
            let (Some(nr), Some(nc)) = (
                r.checked_add_signed(step_row),
                c.checked_add_signed(step_col),
            ) else {
                continue;
            };
            if nr < rows && nc < cols && board[nr][nc] == 'O' {
                board[nr][nc] = SAFE;
                stack.push((nr, nc));
            }
        }
    }
    for row in board.iter_mut() {
        for cell in row.iter_mut() {
            *cell = if *cell == SAFE { 'O' } else { 'X' };
        }
    }
}
