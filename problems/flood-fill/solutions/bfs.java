import java.util.*;

public class Solution {
    private static final int[][] STEPS = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};

    public int[][] floodFill(int[][] grid, int row, int col, int newColor) {
        int oldColor = grid[row][col];
        if (oldColor == newColor) {
            return grid;
        }
        int rows = grid.length;
        int cols = grid[0].length;
        Queue<int[]> queue = new ArrayDeque<>();
        grid[row][col] = newColor;
        queue.add(new int[] {row, col});
        while (!queue.isEmpty()) {
            int[] cell = queue.poll();
            for (int[] step : STEPS) {
                int r = cell[0] + step[0];
                int c = cell[1] + step[1];
                if (r >= 0 && r < rows && c >= 0 && c < cols && grid[r][c] == oldColor) {
                    grid[r][c] = newColor;
                    queue.add(new int[] {r, c});
                }
            }
        }
        return grid;
    }
}
