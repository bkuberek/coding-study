import java.util.*;

public class Solution {
    private static final int[][] STEPS = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};

    public int[][] pacificAtlantic(int[][] heights) {
        int rows = heights.length;
        int cols = heights[0].length;
        // seen[r][c] == start marks cells visited by the search from start; no clearing needed.
        int[][] seen = new int[rows][cols];
        for (int[] row : seen) {
            Arrays.fill(row, -1);
        }
        List<int[]> cells = new ArrayList<>();
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                if (drainsToBoth(heights, seen, r, c)) {
                    cells.add(new int[] {r, c});
                }
            }
        }
        return cells.toArray(new int[0][]);
    }

    private boolean drainsToBoth(int[][] heights, int[][] seen, int startR, int startC) {
        int rows = heights.length;
        int cols = heights[0].length;
        int start = startR * cols + startC;
        boolean pacific = false;
        boolean atlantic = false;
        Deque<int[]> stack = new ArrayDeque<>();
        seen[startR][startC] = start;
        stack.push(new int[] {startR, startC});
        while (!stack.isEmpty()) {
            int[] cell = stack.pop();
            int r = cell[0];
            int c = cell[1];
            pacific |= r == 0 || c == 0;
            atlantic |= r == rows - 1 || c == cols - 1;
            if (pacific && atlantic) {
                return true;
            }
            for (int[] step : STEPS) {
                int nr = r + step[0];
                int nc = c + step[1];
                if (nr >= 0 && nr < rows && nc >= 0 && nc < cols
                        && seen[nr][nc] != start && heights[nr][nc] <= heights[r][c]) {
                    seen[nr][nc] = start;
                    stack.push(new int[] {nr, nc});
                }
            }
        }
        return false;
    }
}
