pub fn solve_n_queens(n: i32) -> Vec<Vec<String>> {
    let n = n as usize;
    let full: u32 = (1 << n) - 1;
    let mut boards = Vec::new();
    let mut queen_column = Vec::with_capacity(n);
    place(full, [0, 0, 0], &mut queen_column, &mut boards);
    boards
}

/// Each mask marks the squares of the current row attacked along one kind of line: `attacked`
/// holds the columns, the diagonals and the anti-diagonals, in that order.
fn place(
    full: u32,
    attacked: [u32; 3],
    queen_column: &mut Vec<usize>,
    boards: &mut Vec<Vec<String>>,
) {
    let [columns, diagonals, anti_diagonals] = attacked;
    if columns == full {
        boards.push(draw(queen_column));
        return;
    }
    let mut free = full & !(columns | diagonals | anti_diagonals);
    while free != 0 {
        let bit = free & free.wrapping_neg(); // lowest free square
        free ^= bit;
        queen_column.push(bit.trailing_zeros() as usize);
        // Moving one row down shifts each diagonal attack one column over.
        let next = [
            columns | bit,
            ((diagonals | bit) << 1) & full,
            (anti_diagonals | bit) >> 1,
        ];
        place(full, next, queen_column, boards);
        queen_column.pop();
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
