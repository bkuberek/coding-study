import java.util.*;

public class Solution {
    private static final int[][] STEPS = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};

    public int shortestPath(int[][] grid, int k) {
        int rows = grid.length;
        int cols = grid[0].length;
        // Enough removals for the straight Manhattan route: nothing can beat it.
        if (k >= rows + cols - 3) {
            return rows + cols - 2;
        }
        // best[r][c] is the most removals left with which (r, c) was reached so far.
        int[][] best = new int[rows][cols];
        for (int[] row : best) {
            Arrays.fill(row, -1);
        }
        best[0][0] = k;
        Queue<int[]> queue = new ArrayDeque<>();
        queue.add(new int[] {0, 0, k});
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
                    int remaining = state[2] - grid[nr][nc];
                    // A visit that arrives later with no more removals left can never do better.
                    if (remaining > best[nr][nc]) {
                        best[nr][nc] = remaining;
                        queue.add(new int[] {nr, nc, remaining});
                    }
                }
            }
        }
        return -1;
    }
}
