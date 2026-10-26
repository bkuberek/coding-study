public class Solution {
    public void setZeroes(int[][] matrix) {
        int rows = matrix.length;
        int cols = matrix[0].length;
        // Find every row and column to clear before clearing anything.
        boolean[] zeroRows = new boolean[rows];
        boolean[] zeroCols = new boolean[cols];
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                if (matrix[r][c] == 0) {
                    zeroRows[r] = true;
                    zeroCols[c] = true;
                }
            }
        }
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                if (zeroRows[r] || zeroCols[c]) {
                    matrix[r][c] = 0;
                }
            }
        }
    }
}
