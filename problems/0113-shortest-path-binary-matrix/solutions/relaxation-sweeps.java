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
        int unreached = n * n + 1;
        int[][] dist = new int[n][n];
        for (int[] row : dist) {
            Arrays.fill(row, unreached);
        }
        dist[0][0] = 1;
        boolean forward = true;
        boolean changed = true;
        while (changed) {
            changed = false;
            // Each sweep lets every open cell take the best distance offered by a neighbor;
            // alternating the scan direction lets improvements travel both ways quickly.
            for (int i = 0; i < n * n; i++) {
                int cell = forward ? i : n * n - 1 - i;
                int r = cell / n;
                int c = cell % n;
                if (grid[r][c] == 1) {
                    continue;
                }
                for (int[] step : STEPS) {
                    int nr = r + step[0];
                    int nc = c + step[1];
                    if (nr >= 0 && nr < n && nc >= 0 && nc < n && dist[nr][nc] + 1 < dist[r][c]) {
                        dist[r][c] = dist[nr][nc] + 1;
                        changed = true;
                    }
                }
            }
            forward = !forward;
        }
        return dist[n - 1][n - 1] < unreached ? dist[n - 1][n - 1] : -1;
    }
}
