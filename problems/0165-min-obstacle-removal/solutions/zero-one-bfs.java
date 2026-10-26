import java.util.*;

public class Solution {
    private static final int[][] STEPS = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};

    public int minimumObstacles(int[][] grid) {
        int rows = grid.length;
        int cols = grid[0].length;
        int[][] removals = new int[rows][cols];
        for (int[] row : removals) {
            Arrays.fill(row, Integer.MAX_VALUE);
        }
        removals[0][0] = 0;
        // The deque stays sorted by removals: zero-cost steps go to the front, one-cost steps
        // to the back, so its two ends never differ by more than one.
        Deque<int[]> deque = new ArrayDeque<>();
        deque.add(new int[] {0, 0});
        while (!deque.isEmpty()) {
            int[] cell = deque.pollFirst();
            int r = cell[0];
            int c = cell[1];
            int cost = removals[r][c];
            if (r == rows - 1 && c == cols - 1) {
                return cost;
            }
            for (int[] step : STEPS) {
                int nr = r + step[0];
                int nc = c + step[1];
                if (nr < 0 || nr >= rows || nc < 0 || nc >= cols) {
                    continue;
                }
                int offered = cost + grid[nr][nc];
                if (offered < removals[nr][nc]) {
                    removals[nr][nc] = offered;
                    if (grid[nr][nc] == 0) {
                        deque.addFirst(new int[] {nr, nc});
                    } else {
                        deque.addLast(new int[] {nr, nc});
                    }
                }
            }
        }
        return removals[rows - 1][cols - 1];
    }
}
