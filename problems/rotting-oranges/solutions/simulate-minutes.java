import java.util.*;

public class Solution {
    private static final int FRESH = 1;
    private static final int ROTTEN = 2;

    public int orangesRotting(int[][] grid) {
        int rows = grid.length;
        int cols = grid[0].length;
        int minutes = 0;
        while (true) {
            // Collect this minute's changes before applying any, so new rot waits a minute.
            List<int[]> turning = new ArrayList<>();
            for (int r = 0; r < rows; r++) {
                for (int c = 0; c < cols; c++) {
                    if (grid[r][c] == FRESH && touchesRot(grid, r, c)) {
                        turning.add(new int[] {r, c});
                    }
                }
            }
            if (turning.isEmpty()) {
                break;
            }
            for (int[] cell : turning) {
                grid[cell[0]][cell[1]] = ROTTEN;
            }
            minutes++;
        }
        for (int[] row : grid) {
            for (int cell : row) {
                if (cell == FRESH) {
                    return -1;
                }
            }
        }
        return minutes;
    }

    private boolean touchesRot(int[][] grid, int r, int c) {
        return (r > 0 && grid[r - 1][c] == ROTTEN)
                || (r + 1 < grid.length && grid[r + 1][c] == ROTTEN)
                || (c > 0 && grid[r][c - 1] == ROTTEN)
                || (c + 1 < grid[0].length && grid[r][c + 1] == ROTTEN);
    }
}
