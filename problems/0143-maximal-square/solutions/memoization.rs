pub fn maximal_square(matrix: Vec<Vec<char>>) -> i32 {
    let (rows, columns) = (matrix.len(), matrix[0].len());
    // side[r][c] caches the largest all-ones square with its top-left corner at (r, c);
    // None is unknown.
    let mut side = vec![vec![None; columns]; rows];
    let mut best = 0;
    for r in 0..rows {
        for c in 0..columns {
            best = best.max(largest(r, c, &matrix, &mut side));
        }
    }
    best * best
}

fn largest(r: usize, c: usize, matrix: &[Vec<char>], side: &mut [Vec<Option<i32>>]) -> i32 {
    if r == matrix.len() || c == matrix[0].len() || matrix[r][c] == '0' {
        return 0;
    }
    if let Some(known) = side[r][c] {
        return known;
    }
    let down = largest(r + 1, c, matrix, side);
    let right = largest(r, c + 1, matrix, side);
    let diagonal = largest(r + 1, c + 1, matrix, side);
    let result = 1 + down.min(right).min(diagonal);
    side[r][c] = Some(result);
    result
}
