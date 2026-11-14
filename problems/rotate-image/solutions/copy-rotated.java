public class Solution {
    public void rotate(int[][] matrix) {
        int n = matrix.length;
        // Row r of the rotated image is column r of the original, read from bottom to top.
        int[][] rotated = new int[n][n];
        for (int r = 0; r < n; r++) {
            for (int c = 0; c < n; c++) {
                rotated[c][n - 1 - r] = matrix[r][c];
            }
        }
        for (int r = 0; r < n; r++) {
            System.arraycopy(rotated[r], 0, matrix[r], 0, n);
        }
    }
}
