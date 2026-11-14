use std::collections::HashSet;

// The stub fixes the parameter as `&mut Vec<Vec<i32>>`; this reference only needs slice operations.
#[allow(clippy::ptr_arg)]
pub fn set_zeroes(matrix: &mut Vec<Vec<i32>>) {
    // Find every row and column to clear before clearing anything.
    let mut zero_rows = HashSet::new();
    let mut zero_cols = HashSet::new();
    for (r, row) in matrix.iter().enumerate() {
        for (c, &value) in row.iter().enumerate() {
            if value == 0 {
                zero_rows.insert(r);
                zero_cols.insert(c);
            }
        }
    }
    for (r, row) in matrix.iter_mut().enumerate() {
        for (c, cell) in row.iter_mut().enumerate() {
            if zero_rows.contains(&r) || zero_cols.contains(&c) {
                *cell = 0;
            }
        }
    }
}
