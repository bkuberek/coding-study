import java.util.*;

public class Solution {
    private static final int MOD = 1_000_000_007;

    // routes[row][column] caches the number of routes from that cell to the goal; -1 is unknown.
    private int[][] routes;

    public int uniquePaths(int m, int n) {
        routes = new int[m][n];
        for (int[] row : routes) {
            Arrays.fill(row, -1);
        }
        return count(0, 0);
    }

    private int count(int row, int column) {
        if (row == routes.length - 1 || column == routes[0].length - 1) {
            return 1;
        }
        if (routes[row][column] < 0) {
            // Two values below MOD add up to less than 2^31, so int addition is safe.
            routes[row][column] = (count(row + 1, column) + count(row, column + 1)) % MOD;
        }
        return routes[row][column];
    }
}
