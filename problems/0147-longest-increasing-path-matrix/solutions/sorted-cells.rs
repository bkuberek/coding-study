use std::cmp::Reverse;

const STEPS: [(isize, isize); 4] = [(1, 0), (-1, 0), (0, 1), (0, -1)];

pub fn longest_increasing_path(matrix: Vec<Vec<i32>>) -> i32 {
    let (rows, columns) = (matrix.len(), matrix[0].len());
    // longest[r][c] is the longest increasing path starting at (r, c).
    let mut longest = vec![vec![1; columns]; rows];
    // Every larger neighbor comes earlier in decreasing order of value, so its entry is final
    // when the cell is processed. Equal neighbors are never steps, so ties may go either way.
    let mut order: Vec<(usize, usize)> = (0..rows)
        .flat_map(|r| (0..columns).map(move |c| (r, c)))
        .collect();
    order.sort_by_key(|&(r, c)| Reverse(matrix[r][c]));
    let mut result = 0;
    for (r, c) in order {
        for (dr, dc) in STEPS {
            let (Some(nr), Some(nc)) = (r.checked_add_signed(dr), c.checked_add_signed(dc)) else {
                continue;
            };
            if nr < rows && nc < columns && matrix[nr][nc] > matrix[r][c] {
                longest[r][c] = longest[r][c].max(1 + longest[nr][nc]);
            }
        }
        result = result.max(longest[r][c]);
    }
    result
}
