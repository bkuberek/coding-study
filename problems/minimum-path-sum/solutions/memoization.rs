const UNKNOWN: i32 = -1;

pub fn min_path_sum(grid: Vec<Vec<i32>>) -> i32 {
    let rows = grid.len();
    let columns = grid[0].len();
    let mut cheapest = vec![vec![UNKNOWN; columns]; rows];
    cheapest_to(&grid, &mut cheapest, rows - 1, columns - 1)
}

fn cheapest_to(grid: &[Vec<i32>], cheapest: &mut [Vec<i32>], row: usize, column: usize) -> i32 {
    if cheapest[row][column] != UNKNOWN {
        return cheapest[row][column];
    }
    let arrival = if row == 0 && column == 0 {
        0
    } else if row == 0 {
        cheapest_to(grid, cheapest, row, column - 1)
    } else if column == 0 {
        cheapest_to(grid, cheapest, row - 1, column)
    } else {
        let above = cheapest_to(grid, cheapest, row - 1, column);
        let left = cheapest_to(grid, cheapest, row, column - 1);
        above.min(left)
    };
    cheapest[row][column] = arrival + grid[row][column];
    cheapest[row][column]
}
