import java.util.*;

public class Solution {
    private static final int[][] STEPS = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};

    public int swimInWater(int[][] grid) {
        int n = grid.length;
        // The answer is at least both corner heights and at most the highest floor.
        int low = Math.max(grid[0][0], grid[n - 1][n - 1]);
        int high = n * n - 1;
        while (low < high) {
            int middle = (low + high) >>> 1;
            if (reachable(grid, middle)) {
                high = middle;
            } else {
                low = middle + 1;
            }
        }
        return low;
    }

    /** Can the goal be reached when the water stands at {@code time}? */
    private boolean reachable(int[][] grid, int time) {
        int n = grid.length;
        if (grid[0][0] > time) {
            return false;
        }
        boolean[][] seen = new boolean[n][n];
        seen[0][0] = true;
        Queue<int[]> queue = new ArrayDeque<>();
        queue.add(new int[] {0, 0});
        while (!queue.isEmpty()) {
            int[] cell = queue.poll();
            if (cell[0] == n - 1 && cell[1] == n - 1) {
                return true;
            }
            for (int[] step : STEPS) {
                int r = cell[0] + step[0];
                int c = cell[1] + step[1];
                if (r >= 0 && r < n && c >= 0 && c < n && !seen[r][c] && grid[r][c] <= time) {
                    seen[r][c] = true;
                    queue.add(new int[] {r, c});
                }
            }
        }
        return false;
    }
}
