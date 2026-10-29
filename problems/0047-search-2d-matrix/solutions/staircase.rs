use std::cmp::Ordering;

pub fn search_matrix(matrix: Vec<Vec<i32>>, target: i32) -> bool {
    // Everything left of the current cell in its row is smaller or equal; everything
    // below it in its column is larger or equal. The column is signed because it reaches -1.
    let (mut row, mut column) = (0, matrix[0].len() as i32 - 1);
    while row < matrix.len() && column >= 0 {
        match matrix[row][column as usize].cmp(&target) {
            Ordering::Equal => return true,
            Ordering::Greater => column -= 1,
            Ordering::Less => row += 1,
        }
    }
    false
}
