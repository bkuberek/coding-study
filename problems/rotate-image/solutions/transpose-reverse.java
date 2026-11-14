public class Solution {
    public void rotate(int[][] matrix) {
        int n = matrix.length;
        // Reflect across the main diagonal, then mirror every row left to right.
        for (int r = 0; r < n; r++) {
            for (int c = r + 1; c < n; c++) {
                int value = matrix[r][c];
                matrix[r][c] = matrix[c][r];
                matrix[c][r] = value;
            }
        }
        for (int[] row : matrix) {
            for (int left = 0, right = n - 1; left < right; left++, right--) {
                int value = row[left];
                row[left] = row[right];
                row[right] = value;
            }
        }
    }
}
