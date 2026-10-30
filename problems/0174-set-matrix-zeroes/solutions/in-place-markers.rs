// The stub fixes the parameter as `&mut Vec<Vec<i32>>`; this reference only needs slice operations.
#[allow(clippy::ptr_arg)]
pub fn set_zeroes(matrix: &mut Vec<Vec<i32>>) {
    let (rows, cols) = (matrix.len(), matrix[0].len());
    // matrix[r][0] marks row r (matrix[0][0] marks row 0) and matrix[0][c] marks column c
    // for c >= 1; column 0 needs its own flag, because matrix[0][0] is taken.
    let mut first_col_has_zero = false;
    for r in 0..rows {
        if matrix[r][0] == 0 {
            first_col_has_zero = true;
        }
        for c in 1..cols {
            if matrix[r][c] == 0 {
                matrix[r][0] = 0;
                matrix[0][c] = 0;
            }
        }
    }
    // Bottom-up, so the markers in row 0 are read before row 0 itself is cleared.
    for r in (0..rows).rev() {
        for c in (1..cols).rev() {
            if matrix[r][0] == 0 || matrix[0][c] == 0 {
                matrix[r][c] = 0;
            }
        }
        if first_col_has_zero {
            matrix[r][0] = 0;
        }
    }
}
