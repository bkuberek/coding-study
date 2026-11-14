use std::cmp::Ordering;

pub fn search_matrix(matrix: Vec<Vec<i32>>, target: i32) -> bool {
    let columns = matrix[0].len() as i32;
    // The bounds are signed because `high` reaches -1 when the target is smaller than every cell.
    let (mut low, mut high) = (0, matrix.len() as i32 * columns - 1);
    while low <= high {
        let middle = low + (high - low) / 2;
        match matrix[(middle / columns) as usize][(middle % columns) as usize].cmp(&target) {
            Ordering::Equal => return true,
            Ordering::Less => low = middle + 1,
            Ordering::Greater => high = middle - 1,
        }
    }
    false
}
