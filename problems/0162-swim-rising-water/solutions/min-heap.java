import java.util.*;

public class Solution {
    private static final int[][] STEPS = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};

    public int swimInWater(int[][] grid) {
        int n = grid.length;
        boolean[][] seen = new boolean[n][n];
        seen[0][0] = true;
        // Entries are {highest floor on the route so far, row, column}.
        PriorityQueue<int[]> heap = new PriorityQueue<>(Comparator.comparingInt(entry -> entry[0]));
        heap.add(new int[] {grid[0][0], 0, 0});
        while (true) {
            int[] entry = heap.poll();
            int level = entry[0];
            if (entry[1] == n - 1 && entry[2] == n - 1) {
                return level;
            }
            for (int[] step : STEPS) {
                int r = entry[1] + step[0];
                int c = entry[2] + step[1];
                if (r >= 0 && r < n && c >= 0 && c < n && !seen[r][c]) {
                    seen[r][c] = true;
                    heap.add(new int[] {Math.max(level, grid[r][c]), r, c});
                }
            }
        }
    }
}
