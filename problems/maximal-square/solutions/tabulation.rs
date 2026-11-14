pub fn maximal_square(matrix: Vec<Vec<char>>) -> i32 {
    let (rows, columns) = (matrix.len(), matrix[0].len());
    // side[r + 1][c + 1] is the largest all-ones square with its bottom-right corner at (r, c);
    // row 0 and column 0 are a border of zeros.
    let mut side = vec![vec![0; columns + 1]; rows + 1];
    let mut best = 0;
    for r in 0..rows {
        for c in 0..columns {
            if matrix[r][c] == '1' {
                side[r + 1][c + 1] = 1 + side[r][c + 1].min(side[r + 1][c]).min(side[r][c]);
                best = best.max(side[r + 1][c + 1]);
            }
        }
    }
    best * best
}
