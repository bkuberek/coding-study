const FRESH: i32 = 1;
const ROTTEN: i32 = 2;

fn touches_rotten(grid: &[Vec<i32>], r: usize, c: usize) -> bool {
    [(1isize, 0isize), (-1, 0), (0, 1), (0, -1)]
        .into_iter()
        .any(|(step_row, step_col)| {
            let (Some(nr), Some(nc)) = (
                r.checked_add_signed(step_row),
                c.checked_add_signed(step_col),
            ) else {
                return false;
            };
            grid.get(nr).and_then(|row| row.get(nc)) == Some(&ROTTEN)
        })
}

pub fn oranges_rotting(mut grid: Vec<Vec<i32>>) -> i32 {
    let mut minutes = 0;
    loop {
        // Decide every change of this minute first, then apply them all: an orange that
        // turns now must not spread rot until the next minute.
        let mut turning = Vec::new();
        for r in 0..grid.len() {
            for c in 0..grid[r].len() {
                if grid[r][c] == FRESH && touches_rotten(&grid, r, c) {
                    turning.push((r, c));
                }
            }
        }
        if turning.is_empty() {
            break;
        }
        for (r, c) in turning {
            grid[r][c] = ROTTEN;
        }
        minutes += 1;
    }
    let fresh_left = grid.iter().any(|row| row.contains(&FRESH));
    if fresh_left {
        -1
    } else {
        minutes
    }
}
