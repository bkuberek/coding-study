public class Solution {
    public void setZeroes(int[][] matrix) {
        int rows = matrix.length;
        int cols = matrix[0].length;
        // matrix[r][0] marks row r (matrix[0][0] marks row 0) and matrix[0][c] marks column c
        // for c >= 1; column 0 needs its own flag, because matrix[0][0] is taken.
        boolean firstColHasZero = false;
        for (int r = 0; r < rows; r++) {
            if (matrix[r][0] == 0) {
                firstColHasZero = true;
            }
            for (int c = 1; c < cols; c++) {
                if (matrix[r][c] == 0) {
                    matrix[r][0] = 0;
                    matrix[0][c] = 0;
                }
            }
        }
        // Bottom-up, so the markers in row 0 are read before row 0 itself is cleared.
        for (int r = rows - 1; r >= 0; r--) {
            for (int c = cols - 1; c >= 1; c--) {
                if (matrix[r][0] == 0 || matrix[0][c] == 0) {
                    matrix[r][c] = 0;
                }
            }
            if (firstColHasZero) {
                matrix[r][0] = 0;
            }
        }
    }
}
