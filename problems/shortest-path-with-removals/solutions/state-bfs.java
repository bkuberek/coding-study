import java.util.*;

public class Solution {
    private static final int[][] STEPS = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};

    public int shortestPath(int[][] grid, int k) {
        int rows = grid.length;
        int cols = grid[0].length;
        // A Manhattan route enters at most rows + cols - 3 cells besides the corners, so more
        // removals than that never help.
        int budget = Math.min(k, Math.max(0, rows + cols - 3));
        boolean[][][] seen = new boolean[rows][cols][budget + 1];
        seen[0][0][0] = true;
        Queue<int[]> queue = new ArrayDeque<>();
        queue.add(new int[] {0, 0, 0});
        for (int moves = 0; !queue.isEmpty(); moves++) {
            for (int i = queue.size(); i > 0; i--) {
                int[] state = queue.poll();
                int r = state[0];
                int c = state[1];
                if (r == rows - 1 && c == cols - 1) {
                    return moves;
                }
                for (int[] step : STEPS) {
                    int nr = r + step[0];
                    int nc = c + step[1];
                    if (nr < 0 || nr >= rows || nc < 0 || nc >= cols) {
                        continue;
                    }
                    int after = state[2] + grid[nr][nc];
                    if (after <= budget && !seen[nr][nc][after]) {
                        seen[nr][nc][after] = true;
                        queue.add(new int[] {nr, nc, after});
                    }
                }
            }
        }
        return -1;
    }
}
