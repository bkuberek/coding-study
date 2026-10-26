import java.util.*;

public class Solution {
    private static final int[][] STEPS = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};

    public int numIslands(char[][] grid) {
        int rows = grid.length;
        int cols = grid[0].length;
        boolean[][] visited = new boolean[rows][cols];
        int islands = 0;
        Queue<int[]> queue = new ArrayDeque<>();
        for (int row = 0; row < rows; row++) {
            for (int col = 0; col < cols; col++) {
                if (grid[row][col] != '1' || visited[row][col]) {
                    continue;
                }
                islands++;
                visited[row][col] = true;
                queue.add(new int[] {row, col});
                while (!queue.isEmpty()) {
                    int[] cell = queue.poll();
                    for (int[] step : STEPS) {
                        int r = cell[0] + step[0];
                        int c = cell[1] + step[1];
                        if (r >= 0 && r < rows && c >= 0 && c < cols && grid[r][c] == '1' && !visited[r][c]) {
                            visited[r][c] = true;
                            queue.add(new int[] {r, c});
                        }
                    }
                }
            }
        }
        return islands;
    }
}
