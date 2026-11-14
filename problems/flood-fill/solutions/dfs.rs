pub fn flood_fill(mut grid: Vec<Vec<i32>>, row: i32, col: i32, new_color: i32) -> Vec<Vec<i32>> {
    let old_color = grid[row as usize][col as usize];
    if old_color != new_color {
        paint(&mut grid, row, col, old_color, new_color);
    }
    grid
}

/// Repaints the square at (`r`, `c`) and, from there, every square of its region.
/// The coordinates are signed so that a step off the top or left edge is just a negative number.
fn paint(grid: &mut [Vec<i32>], r: i32, c: i32, old_color: i32, new_color: i32) {
    if r < 0 || c < 0 {
        return;
    }
    let (row, col) = (r as usize, c as usize);
    if row >= grid.len() || col >= grid[0].len() || grid[row][col] != old_color {
        return;
    }
    grid[row][col] = new_color;
    paint(grid, r + 1, c, old_color, new_color);
    paint(grid, r - 1, c, old_color, new_color);
    paint(grid, r, c + 1, old_color, new_color);
    paint(grid, r, c - 1, old_color, new_color);
}
