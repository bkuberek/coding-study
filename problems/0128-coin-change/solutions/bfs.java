import java.util.*;

public class Solution {
    public int coinChange(int[] coins, int amount) {
        // Remainders are nodes and paying one coin is an edge; the first level that reaches 0
        // is the fewest number of coins.
        boolean[] seen = new boolean[amount + 1];
        seen[amount] = true;
        ArrayDeque<Integer> queue = new ArrayDeque<>();
        queue.add(amount);
        int coinsUsed = 0;
        while (!queue.isEmpty()) {
            if (seen[0]) {
                return coinsUsed;
            }
            for (int size = queue.size(); size > 0; size--) {
                int remaining = queue.poll();
                for (int coin : coins) {
                    int rest = remaining - coin;
                    if (rest >= 0 && !seen[rest]) {
                        seen[rest] = true;
                        queue.add(rest);
                    }
                }
            }
            coinsUsed++;
        }
        return -1;
    }
}
