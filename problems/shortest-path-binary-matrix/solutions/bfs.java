import java.util.*;

public class Solution {
    private static final int[][] STEPS = {
        {-1, -1}, {-1, 0}, {-1, 1}, {0, -1}, {0, 1}, {1, -1}, {1, 0}, {1, 1}
    };

    public int shortestPathBinaryMatrix(int[][] grid) {
        int n = grid.length;
        if (grid[0][0] == 1 || grid[n - 1][n - 1] == 1) {
            return -1;
        }
        // dist 0 means "not reached yet": every reached cell has a length of at least 1.
        int[][] dist = new int[n][n];
        dist[0][0] = 1;
        Queue<int[]> queue = new ArrayDeque<>();
        queue.add(new int[] {0, 0});
        while (!queue.isEmpty()) {
            int[] cell = queue.poll();
            int r = cell[0];
            int c = cell[1];
            if (r == n - 1 && c == n - 1) {
                return dist[r][c];
            }
            for (int[] step : STEPS) {
                int nr = r + step[0];
                int nc = c + step[1];
                if (nr >= 0 && nr < n && nc >= 0 && nc < n && grid[nr][nc] == 0 && dist[nr][nc] == 0) {
                    dist[nr][nc] = dist[r][c] + 1;
                    queue.add(new int[] {nr, nc});
                }
            }
        }
        return -1;
    }
}
