import java.util.*;

public class Solution {
    public int maximalSquare(char[][] matrix) {
        int rows = matrix.length;
        int columns = matrix[0].length;
        // side[r + 1][c + 1] is the largest all-ones square with its bottom-right corner at (r, c);
        // row 0 and column 0 are a border of zeros.
        int[][] side = new int[rows + 1][columns + 1];
        int best = 0;
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < columns; c++) {
                if (matrix[r][c] == '1') {
                    side[r + 1][c + 1] = 1 + Math.min(side[r][c + 1], Math.min(side[r + 1][c], side[r][c]));
                    best = Math.max(best, side[r + 1][c + 1]);
                }
            }
        }
        return best * best;
    }
}
