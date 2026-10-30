// The stub fixes the parameter as `&mut Vec<Vec<i32>>`; this reference only needs slice operations.
#[allow(clippy::ptr_arg)]
pub fn rotate(matrix: &mut Vec<Vec<i32>>) {
    let n = matrix.len();
    // Reflect across the main diagonal, then mirror every row left to right.
    for r in 0..n {
        // Row r and the rows below it are disjoint, so both can be borrowed mutably at once.
        let (above, below) = matrix.split_at_mut(r + 1);
        let row = &mut above[r];
        for (offset, lower) in below.iter_mut().enumerate() {
            std::mem::swap(&mut row[r + 1 + offset], &mut lower[r]);
        }
    }
    for row in matrix.iter_mut() {
        row.reverse();
    }
}
