import java.util.*;

public class Solution {
    private static final int[][] STEPS = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};

    public int longestIncreasingPath(int[][] matrix) {
        int rows = matrix.length;
        int columns = matrix[0].length;
        // Cells are numbered r * columns + c. larger[cell] counts the neighbors a path could
        // still step up to from that cell.
        int[] larger = new int[rows * columns];
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < columns; c++) {
                for (int[] step : STEPS) {
                    int nr = r + step[0];
                    int nc = c + step[1];
                    if (nr >= 0 && nr < rows && nc >= 0 && nc < columns && matrix[nr][nc] > matrix[r][c]) {
                        larger[r * columns + c]++;
                    }
                }
            }
        }
        // Kahn's algorithm from the sinks: each round removes the cells whose larger neighbors
        // are all gone. A cell removed in round k starts a longest path of exactly k cells.
        ArrayDeque<Integer> queue = new ArrayDeque<>();
        for (int cell = 0; cell < rows * columns; cell++) {
            if (larger[cell] == 0) {
                queue.add(cell);
            }
        }
        int rounds = 0;
        while (!queue.isEmpty()) {
            rounds++;
            for (int remaining = queue.size(); remaining > 0; remaining--) {
                int cell = queue.poll();
                int r = cell / columns;
                int c = cell % columns;
                for (int[] step : STEPS) {
                    int nr = r + step[0];
                    int nc = c + step[1];
                    if (nr >= 0 && nr < rows && nc >= 0 && nc < columns && matrix[nr][nc] < matrix[r][c]) {
                        int neighbor = nr * columns + nc;
                        if (--larger[neighbor] == 0) {
                            queue.add(neighbor);
                        }
                    }
                }
            }
        }
        return rounds;
    }
}
