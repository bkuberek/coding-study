import java.util.*;

public class Solution {
    private static final int[][] STEPS = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};

    public int maxAreaOfIsland(int[][] grid) {
        int rows = grid.length;
        int cols = grid[0].length;
        boolean[][] seen = new boolean[rows][cols];
        Deque<int[]> stack = new ArrayDeque<>();
        int best = 0;
        for (int row = 0; row < rows; row++) {
            for (int col = 0; col < cols; col++) {
                if (grid[row][col] != 1 || seen[row][col]) {
                    continue;
                }
                seen[row][col] = true;
                stack.push(new int[] {row, col});
                int area = 0;
                while (!stack.isEmpty()) {
                    int[] cell = stack.pop();
                    area++;
                    for (int[] step : STEPS) {
                        int r = cell[0] + step[0];
                        int c = cell[1] + step[1];
                        if (r >= 0 && r < rows && c >= 0 && c < cols && grid[r][c] == 1 && !seen[r][c]) {
                            seen[r][c] = true;
                            stack.push(new int[] {r, c});
                        }
                    }
                }
                best = Math.max(best, area);
            }
        }
        return best;
    }
}
