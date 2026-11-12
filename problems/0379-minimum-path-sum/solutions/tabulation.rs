pub fn min_path_sum(grid: Vec<Vec<i32>>) -> i32 {
    let rows = grid.len();
    let columns = grid[0].len();
    // cheapest[r][c]: the smallest total toll of any route from the top-left block to block (r, c).
    let mut cheapest = vec![vec![0; columns]; rows];
    for row in 0..rows {
        for column in 0..columns {
            let arrival = if row == 0 && column == 0 {
                0
            } else if row == 0 {
                cheapest[row][column - 1]
            } else if column == 0 {
                cheapest[row - 1][column]
            } else {
                cheapest[row - 1][column].min(cheapest[row][column - 1])
            };
            cheapest[row][column] = arrival + grid[row][column];
        }
    }
    cheapest[rows - 1][columns - 1]
}
