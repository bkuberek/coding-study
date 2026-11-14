public class Solution {
    public int minPathSum(int[][] grid) {
        int rows = grid.length;
        int columns = grid[0].length;
        // cheapest[r][c]: the smallest total toll of any route from the top-left block to block (r, c).
        int[][] cheapest = new int[rows][columns];
        for (int row = 0; row < rows; row++) {
            for (int column = 0; column < columns; column++) {
                int arrival;
                if (row == 0 && column == 0) {
                    arrival = 0;
                } else if (row == 0) {
                    arrival = cheapest[row][column - 1];
                } else if (column == 0) {
                    arrival = cheapest[row - 1][column];
                } else {
                    arrival = Math.min(cheapest[row - 1][column], cheapest[row][column - 1]);
                }
                cheapest[row][column] = arrival + grid[row][column];
            }
        }
        return cheapest[rows - 1][columns - 1];
    }
}
