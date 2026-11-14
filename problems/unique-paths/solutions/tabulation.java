import java.util.*;

public class Solution {
    private static final int MOD = 1_000_000_007;

    public int uniquePaths(int m, int n) {
        // routes[row][column] is the number of routes from the start to that cell. The first row
        // and the first column can only be reached in a straight line.
        int[][] routes = new int[m][n];
        for (int[] row : routes) {
            Arrays.fill(row, 1);
        }
        for (int row = 1; row < m; row++) {
            for (int column = 1; column < n; column++) {
                routes[row][column] = (routes[row - 1][column] + routes[row][column - 1]) % MOD;
            }
        }
        return routes[m - 1][n - 1];
    }
}
