pub fn maximal_rectangle(matrix: Vec<Vec<char>>) -> i32 {
    let (rows, columns) = (matrix.len(), matrix[0].len());
    // width[r][c] is the number of consecutive ones ending at (r, c) in row r.
    let mut width = vec![vec![0; columns]; rows];
    let mut best = 0;
    for r in 0..rows {
        for c in 0..columns {
            if matrix[r][c] == '0' {
                continue;
            }
            width[r][c] = if c > 0 { width[r][c - 1] + 1 } else { 1 };
            // Rectangles with bottom-right corner (r, c): extend upwards one row at a time; the
            // rectangle is as wide as the narrowest row it spans.
            let mut narrowest = width[r][c];
            for top in (0..=r).rev() {
                narrowest = narrowest.min(width[top][c]);
                if narrowest == 0 {
                    break;
                }
                best = best.max(narrowest * (r + 1 - top) as i32);
            }
        }
    }
    best
}
