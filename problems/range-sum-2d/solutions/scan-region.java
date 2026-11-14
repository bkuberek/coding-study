public class NumMatrix {
    private final int[][] matrix;

    public NumMatrix(int[][] matrix) {
        this.matrix = matrix;
    }

    public int sumRegion(int row1, int col1, int row2, int col2) {
        int total = 0;
        for (int row = row1; row <= row2; row++) {
            for (int col = col1; col <= col2; col++) {
                total += matrix[row][col];
            }
        }
        return total;
    }
}
