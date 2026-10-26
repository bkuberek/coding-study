public class Solution {
    public boolean searchMatrix(int[][] matrix, int target) {
        // Everything left of the current cell in its row is smaller or equal; everything
        // below it in its column is larger or equal.
        int row = 0;
        int column = matrix[0].length - 1;
        while (row < matrix.length && column >= 0) {
            int value = matrix[row][column];
            if (value == target) {
                return true;
            }
            if (value > target) {
                column--;
            } else {
                row++;
            }
        }
        return false;
    }
}
