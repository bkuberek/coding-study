pub fn spiral_order(matrix: Vec<Vec<i32>>) -> Vec<i32> {
    // The bounds are half-open: `bottom` and `right` are one past the last row and column, so
    // shrinking them never goes below zero.
    let (mut top, mut bottom) = (0, matrix.len());
    let (mut left, mut right) = (0, matrix[0].len());
    let mut order = Vec::with_capacity(bottom * right);
    while top < bottom && left < right {
        order.extend_from_slice(&matrix[top][left..right]);
        order.extend(matrix[top + 1..bottom].iter().map(|row| row[right - 1]));
        if bottom - top > 1 && right - left > 1 {
            // Only a ring with two rows and two columns has a bottom row and left column of its own.
            order.extend(matrix[bottom - 1][left..right - 1].iter().rev());
            order.extend(
                matrix[top + 1..bottom - 1]
                    .iter()
                    .rev()
                    .map(|row| row[left]),
            );
        }
        top += 1;
        bottom -= 1;
        left += 1;
        right -= 1;
    }
    order
}
