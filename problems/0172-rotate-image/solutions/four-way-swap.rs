// The stub fixes the parameter as `&mut Vec<Vec<i32>>`; this reference only needs slice operations.
#[allow(clippy::ptr_arg)]
pub fn rotate(matrix: &mut Vec<Vec<i32>>) {
    let n = matrix.len();
    for layer in 0..n / 2 {
        let last = n - 1 - layer;
        for offset in 0..last - layer {
            let top = matrix[layer][layer + offset];
            // left -> top, bottom -> left, right -> bottom, top -> right
            matrix[layer][layer + offset] = matrix[last - offset][layer];
            matrix[last - offset][layer] = matrix[last][last - offset];
            matrix[last][last - offset] = matrix[layer + offset][last];
            matrix[layer + offset][last] = top;
        }
    }
}
