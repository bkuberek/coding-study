import java.util.*;

public class Solution {
    public int maximalRectangle(char[][] matrix) {
        int rows = matrix.length;
        int columns = matrix[0].length;
        // width[r][c] is the number of consecutive ones ending at (r, c) in row r.
        int[][] width = new int[rows][columns];
        int best = 0;
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < columns; c++) {
                if (matrix[r][c] == '0') {
                    continue;
                }
                width[r][c] = c > 0 ? width[r][c - 1] + 1 : 1;
                // Rectangles with bottom-right corner (r, c): extend upwards one row at a time;
                // the rectangle is as wide as the narrowest row it spans.
                int narrowest = width[r][c];
                for (int top = r; top >= 0 && narrowest > 0; top--) {
                    narrowest = Math.min(narrowest, width[top][c]);
                    best = Math.max(best, narrowest * (r - top + 1));
                }
            }
        }
        return best;
    }
}
