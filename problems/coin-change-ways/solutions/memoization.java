import java.util.*;

public class Solution {
    private int[] coins;
    // ways[i][total] caches the combinations for `total` using coins[i:]; -1 is unknown.
    private int[][] ways;

    public int change(int amount, int[] coins) {
        this.coins = coins;
        ways = new int[coins.length][amount + 1];
        for (int[] row : ways) {
            Arrays.fill(row, -1);
        }
        return count(0, amount);
    }

    private int count(int i, int total) {
        if (total == 0) {
            return 1;
        }
        if (i == coins.length) {
            return 0;
        }
        if (ways[i][total] < 0) {
            // Either no coin of value coins[i] is used, or at least one is.
            int skip = count(i + 1, total);
            int use = coins[i] <= total ? count(i, total - coins[i]) : 0;
            ways[i][total] = skip + use;
        }
        return ways[i][total];
    }
}
