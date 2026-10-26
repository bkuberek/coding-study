import java.util.*;

public class Solution {
    private static final int MOD = 1_000_000_007;

    public int uniquePaths(int m, int n) {
        // Transposing the grid does not change the count, so keep the row along the shorter side.
        int width = Math.min(m, n);
        int height = Math.max(m, n);
        // Before the update, routes[column] belongs to the row above; after it, to the current row.
        int[] routes = new int[width];
        Arrays.fill(routes, 1);
        for (int row = 1; row < height; row++) {
            for (int column = 1; column < width; column++) {
                routes[column] = (routes[column] + routes[column - 1]) % MOD;
            }
        }
        return routes[width - 1];
    }
}
