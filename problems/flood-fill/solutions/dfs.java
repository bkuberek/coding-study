public class Solution {
    public int[][] floodFill(int[][] grid, int row, int col, int newColor) {
        int oldColor = grid[row][col];
        if (oldColor != newColor) {
            paint(grid, row, col, oldColor, newColor);
        }
        return grid;
    }

    private void paint(int[][] grid, int r, int c, int oldColor, int newColor) {
        if (r < 0 || r >= grid.length || c < 0 || c >= grid[0].length || grid[r][c] != oldColor) {
            return;
        }
        grid[r][c] = newColor;
        paint(grid, r + 1, c, oldColor, newColor);
        paint(grid, r - 1, c, oldColor, newColor);
        paint(grid, r, c + 1, oldColor, newColor);
        paint(grid, r, c - 1, oldColor, newColor);
    }
}
