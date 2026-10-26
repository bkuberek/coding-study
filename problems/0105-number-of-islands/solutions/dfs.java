import java.util.*;

public class Solution {
    private static final int[][] STEPS = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};

    public int numIslands(char[][] grid) {
        int rows = grid.length;
        int cols = grid[0].length;
        int islands = 0;
        Deque<int[]> stack = new ArrayDeque<>();
        for (int row = 0; row < rows; row++) {
            for (int col = 0; col < cols; col++) {
                if (grid[row][col] != '1') {
                    continue;
                }
                islands++;
                // Sink each land square when it is discovered, so it is pushed at most once.
                grid[row][col] = '0';
                stack.push(new int[] {row, col});
                while (!stack.isEmpty()) {
                    int[] cell = stack.pop();
                    for (int[] step : STEPS) {
                        int r = cell[0] + step[0];
                        int c = cell[1] + step[1];
                        if (r >= 0 && r < rows && c >= 0 && c < cols && grid[r][c] == '1') {
                            grid[r][c] = '0';
                            stack.push(new int[] {r, c});
                        }
                    }
                }
            }
        }
        return islands;
    }
}
