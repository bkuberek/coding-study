import java.util.*;

public class Solution {
    private static final int[][] STEPS = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};
    private static final int CELL_BITS = 16;

    public int longestIncreasingPath(int[][] matrix) {
        int rows = matrix.length;
        int columns = matrix[0].length;
        // Pack (value, cell) into one long so a primitive sort orders the cells by value;
        // cells are numbered r * columns + c, below 2^16.
        long[] keys = new long[rows * columns];
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < columns; c++) {
                keys[r * columns + c] = ((long) matrix[r][c] << CELL_BITS) | (r * columns + c);
            }
        }
        Arrays.sort(keys);
        // longest[cell] is the longest increasing path starting at that cell. Walking the keys
        // from the largest value down, every larger neighbor is already final.
        int[] longest = new int[rows * columns];
        int answer = 0;
        for (int k = keys.length - 1; k >= 0; k--) {
            int cell = (int) (keys[k] & ((1L << CELL_BITS) - 1));
            int r = cell / columns;
            int c = cell % columns;
            int best = 1;
            for (int[] step : STEPS) {
                int nr = r + step[0];
                int nc = c + step[1];
                if (nr >= 0 && nr < rows && nc >= 0 && nc < columns && matrix[nr][nc] > matrix[r][c]) {
                    best = Math.max(best, 1 + longest[nr * columns + nc]);
                }
            }
            longest[cell] = best;
            answer = Math.max(answer, best);
        }
        return answer;
    }
}
