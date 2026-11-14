import java.util.*;

public class Solution {
    public int change(int amount, int[] coins) {
        // ways[i][total] is the number of combinations for `total` using only coins[:i].
        int[][] ways = new int[coins.length + 1][amount + 1];
        ways[0][0] = 1;
        for (int i = 1; i <= coins.length; i++) {
            int coin = coins[i - 1];
            for (int total = 0; total <= amount; total++) {
                // Combinations without this coin, plus those that use it at least once.
                ways[i][total] = ways[i - 1][total];
                if (total >= coin) {
                    ways[i][total] += ways[i][total - coin];
                }
            }
        }
        return ways[coins.length][amount];
    }
}
