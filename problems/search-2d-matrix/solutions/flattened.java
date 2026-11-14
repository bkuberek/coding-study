public class Solution {
    public boolean searchMatrix(int[][] matrix, int target) {
        int columns = matrix[0].length;
        int low = 0;
        int high = matrix.length * columns - 1;
        while (low <= high) {
            int middle = (low + high) >>> 1;
            int value = matrix[middle / columns][middle % columns];
            if (value == target) {
                return true;
            }
            if (value < target) {
                low = middle + 1;
            } else {
                high = middle - 1;
            }
        }
        return false;
    }
}
