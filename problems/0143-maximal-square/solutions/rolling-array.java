import java.util.*;

public class Solution {
    public int maximalSquare(char[][] matrix) {
        int columns = matrix[0].length;
        // side[c + 1] is the largest square ending at column c of the current row (before the
        // update: of the row above); side[0] is a border of zeros.
        int[] side = new int[columns + 1];
        int best = 0;
        for (char[] row : matrix) {
            int diagonal = 0; // the row-above value of the previous column, saved before it is overwritten
            for (int c = 1; c <= columns; c++) {
                int above = side[c];
                side[c] = row[c - 1] == '1' ? 1 + Math.min(above, Math.min(side[c - 1], diagonal)) : 0;
                best = Math.max(best, side[c]);
                diagonal = above;
            }
        }
        return best * best;
    }
}
