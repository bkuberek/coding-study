import java.util.*;

public class Solution {
    public int change(int amount, int[] coins) {
        // After processing a prefix of the coins, ways[total] counts the combinations for `total`
        // that use only those coins.
        int[] ways = new int[amount + 1];
        ways[0] = 1;
        for (int coin : coins) {
            // Increasing totals: ways[total - coin] already allows this coin, so it can repeat.
            for (int total = coin; total <= amount; total++) {
                ways[total] += ways[total - coin];
            }
        }
        return ways[amount];
    }
}
