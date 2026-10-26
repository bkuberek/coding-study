import java.util.*;

public class Solution {
    private static final int[][] STEPS = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};

    public int[][] burnTimes(int[][] grid) {
        int rows = grid.length;
        int cols = grid[0].length;
        int[][] times = new int[rows][cols];
        for (int[] row : times) {
            Arrays.fill(row, -1);
        }
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                if (grid[r][c] == 2) {
                    times[r][c] = 0;
                }
            }
        }

        int[][] current = grid;
        int minute = 0;
        boolean spreading = true;
        while (spreading) {
            minute++;
            spreading = false;
            int[][] upcoming = new int[rows][];
            for (int r = 0; r < rows; r++) {
                upcoming[r] = current[r].clone();
            }
            for (int r = 0; r < rows; r++) {
                for (int c = 0; c < cols; c++) {
                    if (current[r][c] != 2) {
                        continue;
                    }
                    for (int[] step : STEPS) {
                        int nr = r + step[0];
                        int nc = c + step[1];
                        if (nr >= 0 && nr < rows && nc >= 0 && nc < cols && current[nr][nc] == 1) {
                            upcoming[nr][nc] = 2;
                            times[nr][nc] = minute;
                            spreading = true;
                        }
                    }
                }
            }
            current = upcoming;
        }
        return times;
    }
}
