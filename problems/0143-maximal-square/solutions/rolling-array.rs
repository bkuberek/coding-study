pub fn maximal_square(matrix: Vec<Vec<char>>) -> i32 {
    // side[c + 1] is the largest square ending at column c of the current row (before the
    // update: of the row above); side[0] is a border of zeros.
    let mut side = vec![0; matrix[0].len() + 1];
    let mut best = 0;
    for row in &matrix {
        // diagonal is the row-above value of the previous column, saved before it is overwritten.
        let mut diagonal = 0;
        for (c, &cell) in row.iter().enumerate() {
            let above = side[c + 1];
            side[c + 1] = if cell == '1' {
                1 + above.min(side[c]).min(diagonal)
            } else {
                0
            };
            best = best.max(side[c + 1]);
            diagonal = above;
        }
    }
    best * best
}
