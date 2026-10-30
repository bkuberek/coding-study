pub fn maximal_rectangle(matrix: Vec<Vec<char>>) -> i32 {
    let columns = matrix[0].len();
    // For the current row and each column c: height[c] consecutive ones end here in column c,
    // and the rectangle of that height through column c spans columns left[c] .. right[c] - 1.
    let mut height = vec![0; columns];
    let mut left = vec![0; columns];
    let mut right = vec![columns; columns];
    let mut best = 0;
    for row in &matrix {
        let mut boundary = 0; // first column after the last zero seen in this row
        for c in 0..columns {
            if row[c] == '1' {
                height[c] += 1;
                left[c] = left[c].max(boundary);
            } else {
                height[c] = 0;
                left[c] = 0;
                boundary = c + 1;
            }
        }
        boundary = columns; // the last zero seen from the right
        for c in (0..columns).rev() {
            if row[c] == '1' {
                right[c] = right[c].min(boundary);
            } else {
                right[c] = columns;
                boundary = c;
            }
        }
        for c in 0..columns {
            best = best.max(height[c] * (right[c] - left[c]) as i32);
        }
    }
    best
}
