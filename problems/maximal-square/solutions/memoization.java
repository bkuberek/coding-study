import java.util.*;

public class Solution {
    private char[][] matrix;
    // side[r][c] caches the largest all-ones square with its top-left corner at (r, c);
    // -1 is unknown.
    private int[][] side;

    public int maximalSquare(char[][] matrix) {
        this.matrix = matrix;
        side = new int[matrix.length][matrix[0].length];
        for (int[] row : side) {
            Arrays.fill(row, -1);
        }
        int best = 0;
        for (int r = 0; r < matrix.length; r++) {
            for (int c = 0; c < matrix[0].length; c++) {
                best = Math.max(best, largest(r, c));
            }
        }
        return best * best;
    }

    private int largest(int r, int c) {
        if (r == matrix.length || c == matrix[0].length || matrix[r][c] == '0') {
            return 0;
        }
        if (side[r][c] < 0) {
            side[r][c] = 1 + Math.min(largest(r + 1, c), Math.min(largest(r, c + 1), largest(r + 1, c + 1)));
        }
        return side[r][c];
    }
}
