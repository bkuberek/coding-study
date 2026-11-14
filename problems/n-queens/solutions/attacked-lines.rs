/// The lines already attacked: columns, diagonals (squares share row - col) and anti-diagonals
/// (squares share row + col). row - col runs from -(n-1) to n-1, so it is stored shifted by n - 1.
struct Lines {
    columns: Vec<bool>,
    diagonals: Vec<bool>,
    anti_diagonals: Vec<bool>,
}

pub fn solve_n_queens(n: i32) -> Vec<Vec<String>> {
    let n = n as usize;
    let mut boards = Vec::new();
    let mut queen_column = Vec::with_capacity(n);
    let mut lines = Lines {
        columns: vec![false; n],
        diagonals: vec![false; 2 * n - 1],
        anti_diagonals: vec![false; 2 * n - 1],
    };
    place(n, 0, &mut lines, &mut queen_column, &mut boards);
    boards
}

fn place(
    n: usize,
    row: usize,
    lines: &mut Lines,
    queen_column: &mut Vec<usize>,
    boards: &mut Vec<Vec<String>>,
) {
    if row == n {
        boards.push(draw(queen_column));
        return;
    }
    for col in 0..n {
        let (diagonal, anti_diagonal) = (row + n - 1 - col, row + col);
        if lines.columns[col] || lines.diagonals[diagonal] || lines.anti_diagonals[anti_diagonal] {
            continue;
        }
        lines.columns[col] = true;
        lines.diagonals[diagonal] = true;
        lines.anti_diagonals[anti_diagonal] = true;
        queen_column.push(col);
        place(n, row + 1, lines, queen_column, boards);
        queen_column.pop();
        lines.columns[col] = false;
        lines.diagonals[diagonal] = false;
        lines.anti_diagonals[anti_diagonal] = false;
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
