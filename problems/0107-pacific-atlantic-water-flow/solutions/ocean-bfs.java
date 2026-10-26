import java.util.*;

public class Solution {
    private static final int[][] STEPS = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};

    public int[][] pacificAtlantic(int[][] heights) {
        int rows = heights.length;
        int cols = heights[0].length;
        Deque<int[]> pacificCoast = new ArrayDeque<>();
        Deque<int[]> atlanticCoast = new ArrayDeque<>();
        boolean[][] pacific = new boolean[rows][cols];
        boolean[][] atlantic = new boolean[rows][cols];
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                if (r == 0 || c == 0) {
                    pacific[r][c] = true;
                    pacificCoast.add(new int[] {r, c});
                }
                if (r == rows - 1 || c == cols - 1) {
                    atlantic[r][c] = true;
                    atlanticCoast.add(new int[] {r, c});
                }
            }
        }
        climb(heights, pacificCoast, pacific);
        climb(heights, atlanticCoast, atlantic);
        List<int[]> cells = new ArrayList<>();
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                if (pacific[r][c] && atlantic[r][c]) {
                    cells.add(new int[] {r, c});
                }
            }
        }
        return cells.toArray(new int[0][]);
    }

    /** Marks every cell whose water reaches the coast: an uphill search from all coast cells. */
    private void climb(int[][] heights, Deque<int[]> queue, boolean[][] reached) {
        int rows = heights.length;
        int cols = heights[0].length;
        while (!queue.isEmpty()) {
            int[] cell = queue.poll();
            for (int[] step : STEPS) {
                int nr = cell[0] + step[0];
                int nc = cell[1] + step[1];
                if (nr >= 0 && nr < rows && nc >= 0 && nc < cols
                        && !reached[nr][nc] && heights[nr][nc] >= heights[cell[0]][cell[1]]) {
                    reached[nr][nc] = true;
                    queue.add(new int[] {nr, nc});
                }
            }
        }
    }
}
