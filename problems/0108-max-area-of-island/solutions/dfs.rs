pub fn max_area_of_island(grid: Vec<Vec<i32>>) -> i32 {
    let rows = grid.len();
    let cols = grid[0].len();
    let mut seen = vec![vec![false; cols]; rows];
    let mut best = 0;
    for row in 0..rows {
        for col in 0..cols {
            if grid[row][col] != 1 || seen[row][col] {
                continue;
            }
            seen[row][col] = true;
            let mut stack = vec![(row, col)];
            let mut area = 0;
            while let Some((r, c)) = stack.pop() {
                area += 1;
                for (step_row, step_col) in [(1isize, 0isize), (-1, 0), (0, 1), (0, -1)] {
                    let (Some(next_row), Some(next_col)) = (
                        r.checked_add_signed(step_row),
                        c.checked_add_signed(step_col),
                    ) else {
                        continue;
                    };
                    if next_row < rows
                        && next_col < cols
                        && grid[next_row][next_col] == 1
                        && !seen[next_row][next_col]
                    {
                        seen[next_row][next_col] = true;
                        stack.push((next_row, next_col));
                    }
                }
            }
            best = best.max(area);
        }
    }
    best
}
