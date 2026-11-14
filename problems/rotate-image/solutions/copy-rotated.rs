pub fn rotate(matrix: &mut Vec<Vec<i32>>) {
    let n = matrix.len();
    // Row r of the rotated image is column r of the original, read from bottom to top.
    let rotated: Vec<Vec<i32>> = (0..n)
        .map(|r| (0..n).map(|c| matrix[n - 1 - c][r]).collect())
        .collect();
    *matrix = rotated;
}
