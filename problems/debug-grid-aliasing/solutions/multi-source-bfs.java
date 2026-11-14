import java.util.*;

public class Solution {
    private static final int[][] STEPS = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};

    public int[][] burnTimes(int[][] grid) {
        int rows = grid.length;
        int cols = grid[0].length;
        int[][] times = new int[rows][cols];
        Deque<int[]> queue = new ArrayDeque<>();
        for (int r = 0; r < rows; r++) {
            Arrays.fill(times[r], -1);
            for (int c = 0; c < cols; c++) {
                if (grid[r][c] == 2) {
                    times[r][c] = 0;
                    queue.add(new int[] {r, c});
                }
            }
        }
        while (!queue.isEmpty()) {
            int[] cell = queue.poll();
            for (int[] step : STEPS) {
                int nr = cell[0] + step[0];
                int nc = cell[1] + step[1];
                if (nr >= 0 && nr < rows && nc >= 0 && nc < cols
                        && grid[nr][nc] == 1 && times[nr][nc] == -1) {
                    times[nr][nc] = times[cell[0]][cell[1]] + 1;
                    queue.add(new int[] {nr, nc});
                }
            }
        }
        return times;
    }
}
