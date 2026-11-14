import java.util.*;

public class Solution {
    private static final int UNKNOWN = -1;

    public int minPathSum(int[][] grid) {
        int rows = grid.length;
        int columns = grid[0].length;
        int[][] cheapest = new int[rows][columns];
        for (int[] row : cheapest) {
            Arrays.fill(row, UNKNOWN);
        }
        return cheapestTo(grid, cheapest, rows - 1, columns - 1);
    }

    private int cheapestTo(int[][] grid, int[][] cheapest, int row, int column) {
        if (cheapest[row][column] != UNKNOWN) {
            return cheapest[row][column];
        }
        int arrival;
        if (row == 0 && column == 0) {
            arrival = 0;
        } else if (row == 0) {
            arrival = cheapestTo(grid, cheapest, row, column - 1);
        } else if (column == 0) {
            arrival = cheapestTo(grid, cheapest, row - 1, column);
        } else {
            arrival = Math.min(
                cheapestTo(grid, cheapest, row - 1, column),
                cheapestTo(grid, cheapest, row, column - 1));
        }
        cheapest[row][column] = arrival + grid[row][column];
        return cheapest[row][column];
    }
}
