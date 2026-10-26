import java.util.*;

public class Solution {
    private static final int[][] STEPS = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};

    public int minimumObstacles(int[][] grid) {
        int rows = grid.length;
        int cols = grid[0].length;
        boolean[][] settled = new boolean[rows][cols];
        // Entries are {removals so far, row, column}; entering a cell costs its own value.
        PriorityQueue<int[]> heap = new PriorityQueue<>(Comparator.comparingInt(entry -> entry[0]));
        heap.add(new int[] {0, 0, 0});
        while (true) {
            int[] entry = heap.poll();
            int cost = entry[0];
            int r = entry[1];
            int c = entry[2];
            if (settled[r][c]) {
                continue; // an outdated entry: settled earlier at a lower cost
            }
            settled[r][c] = true;
            if (r == rows - 1 && c == cols - 1) {
                return cost;
            }
            for (int[] step : STEPS) {
                int nr = r + step[0];
                int nc = c + step[1];
                if (nr >= 0 && nr < rows && nc >= 0 && nc < cols && !settled[nr][nc]) {
                    heap.add(new int[] {cost + grid[nr][nc], nr, nc});
                }
            }
        }
    }
}
