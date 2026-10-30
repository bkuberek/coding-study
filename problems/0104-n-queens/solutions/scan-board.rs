pub fn solve_n_queens(n: i32) -> Vec<Vec<String>> {
    let n = n as usize;
    let mut boards = Vec::new();
    // queen_column[r] is the column of the queen in row r, for the rows placed so far.
    let mut queen_column = Vec::with_capacity(n);
    place(n, 0, &mut queen_column, &mut boards);
    boards
}

fn is_safe(queen_column: &[usize], row: usize, col: usize) -> bool {
    queen_column
        .iter()
        .enumerate()
        .all(|(other_row, &other_col)| {
            col != other_col && col.abs_diff(other_col) != row - other_row
        })
}

fn place(n: usize, row: usize, queen_column: &mut Vec<usize>, boards: &mut Vec<Vec<String>>) {
    if row == n {
        boards.push(draw(queen_column));
        return;
    }
    for col in 0..n {
        if is_safe(queen_column, row, col) {
            queen_column.push(col);
            place(n, row + 1, queen_column, boards);
            queen_column.pop();
        }
    }
}

/// Renders one board, one string per row, from the column of each row's queen.
fn draw(queen_column: &[usize]) -> Vec<String> {
    let size = queen_column.len();
    queen_column
        .iter()
        .map(|&col| format!("{}Q{}", ".".repeat(col), ".".repeat(size - col - 1)))
        .collect()
}
