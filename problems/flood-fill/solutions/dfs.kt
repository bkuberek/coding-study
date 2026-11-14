class Solution {
    fun floodFill(grid: Array<IntArray>, row: Int, col: Int, newColor: Int): Array<IntArray> {
        val oldColor = grid[row][col]
        if (oldColor != newColor) paint(grid, row, col, oldColor, newColor)
        return grid
    }

    private fun paint(grid: Array<IntArray>, r: Int, c: Int, oldColor: Int, newColor: Int) {
        if (r !in grid.indices || c !in grid[0].indices || grid[r][c] != oldColor) return
        grid[r][c] = newColor
        paint(grid, r + 1, c, oldColor, newColor)
        paint(grid, r - 1, c, oldColor, newColor)
        paint(grid, r, c + 1, oldColor, newColor)
        paint(grid, r, c - 1, oldColor, newColor)
    }
}
