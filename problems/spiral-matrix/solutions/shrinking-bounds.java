public class Solution {
    public int[] spiralOrder(int[][] matrix) {
        int top = 0;
        int bottom = matrix.length - 1;
        int left = 0;
        int right = matrix[0].length - 1;
        int[] order = new int[matrix.length * matrix[0].length];
        int filled = 0;
        while (top <= bottom && left <= right) {
            for (int c = left; c <= right; c++) {
                order[filled++] = matrix[top][c];
            }
            for (int r = top + 1; r <= bottom; r++) {
                order[filled++] = matrix[r][right];
            }
            // Only a ring with two rows and two columns has a bottom row and left column of its own.
            if (top < bottom && left < right) {
                for (int c = right - 1; c >= left; c--) {
                    order[filled++] = matrix[bottom][c];
                }
                for (int r = bottom - 1; r > top; r--) {
                    order[filled++] = matrix[r][left];
                }
            }
            top++;
            bottom--;
            left++;
            right--;
        }
        return order;
    }
}
