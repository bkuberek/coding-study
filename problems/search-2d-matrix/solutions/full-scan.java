public class Solution {
    public boolean searchMatrix(int[][] matrix, int target) {
        for (int[] row : matrix) {
            for (int value : row) {
                if (value == target) {
                    return true;
                }
            }
        }
        return false;
    }
}
