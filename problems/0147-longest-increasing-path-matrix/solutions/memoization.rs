const STEPS: [(isize, isize); 4] = [(1, 0), (-1, 0), (0, 1), (0, -1)];

pub fn longest_increasing_path(matrix: Vec<Vec<i32>>) -> i32 {
    let (rows, columns) = (matrix.len(), matrix[0].len());
    // longest[r][c] caches the longest increasing path that starts at (r, c); 0 is unknown.
    let mut longest = vec![vec![0; columns]; rows];
    let mut result = 0;
    for r in 0..rows {
        for c in 0..columns {
            result = result.max(explore(r, c, &matrix, &mut longest));
        }
    }
    result
}

fn explore(r: usize, c: usize, matrix: &[Vec<i32>], longest: &mut [Vec<i32>]) -> i32 {
    if longest[r][c] == 0 {
        let mut best = 1;
        for (dr, dc) in STEPS {
            // A step off the top or left edge makes checked_add_signed return None.
            let (Some(nr), Some(nc)) = (r.checked_add_signed(dr), c.checked_add_signed(dc)) else {
                continue;
            };
            if nr < matrix.len() && nc < matrix[0].len() && matrix[nr][nc] > matrix[r][c] {
                best = best.max(1 + explore(nr, nc, matrix, longest));
            }
        }
        longest[r][c] = best;
    }
    longest[r][c]
}
