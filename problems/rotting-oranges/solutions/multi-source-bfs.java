import java.util.*;

public class Solution {
    private static final int FRESH = 1;
    private static final int ROTTEN = 2;
    private static final int[][] STEPS = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};

    public int orangesRotting(int[][] grid) {
        int rows = grid.length;
        int cols = grid[0].length;
        Queue<int[]> queue = new ArrayDeque<>();
        int fresh = 0;
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                if (grid[r][c] == ROTTEN) {
                    queue.add(new int[] {r, c});
                } else if (grid[r][c] == FRESH) {
                    fresh++;
                }
            }
        }
        int minutes = 0;
        // Each pass of the outer loop rots the whole current frontier: one minute.
        while (!queue.isEmpty() && fresh > 0) {
            minutes++;
            for (int i = queue.size(); i > 0; i--) {
                int[] cell = queue.poll();
                for (int[] step : STEPS) {
                    int r = cell[0] + step[0];
                    int c = cell[1] + step[1];
                    if (r >= 0 && r < rows && c >= 0 && c < cols && grid[r][c] == FRESH) {
                        grid[r][c] = ROTTEN;
                        fresh--;
                        queue.add(new int[] {r, c});
                    }
                }
            }
        }
        return fresh == 0 ? minutes : -1;
    }
}
