import java.util.*;

public class Solution {
    public int maximalRectangle(char[][] matrix) {
        int columns = matrix[0].length;
        // For the current row and each column c: height[c] consecutive ones end here in column c,
        // and the rectangle of that height through column c spans columns left[c] .. right[c] - 1.
        int[] height = new int[columns];
        int[] left = new int[columns];
        int[] right = new int[columns];
        Arrays.fill(right, columns);
        int best = 0;
        for (char[] row : matrix) {
            int boundary = 0; // first column after the last zero seen in this row
            for (int c = 0; c < columns; c++) {
                if (row[c] == '1') {
                    height[c]++;
                    left[c] = Math.max(left[c], boundary);
                } else {
                    height[c] = 0;
                    left[c] = 0;
                    boundary = c + 1;
                }
            }
            boundary = columns; // the last zero seen from the right
            for (int c = columns - 1; c >= 0; c--) {
                if (row[c] == '1') {
                    right[c] = Math.min(right[c], boundary);
                } else {
                    right[c] = columns;
                    boundary = c;
                }
            }
            for (int c = 0; c < columns; c++) {
                best = Math.max(best, height[c] * (right[c] - left[c]));
            }
        }
        return best;
    }
}
