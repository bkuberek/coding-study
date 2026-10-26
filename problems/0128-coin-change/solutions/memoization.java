import java.util.*;

public class Solution {
    private static final int UNKNOWN = -1;

    public int coinChange(int[] coins, int amount) {
        // fewest(x) never exceeds amount + 1, which stands for "x cannot be paid".
        int[] memo = new int[amount + 1];
        Arrays.fill(memo, UNKNOWN);
        int answer = fewest(amount, coins, memo, amount + 1);
        return answer == amount + 1 ? -1 : answer;
    }

    private int fewest(int remaining, int[] coins, int[] memo, int unreachable) {
        if (remaining == 0) {
            return 0;
        }
        if (memo[remaining] == UNKNOWN) {
            int best = unreachable;
            for (int coin : coins) {
                if (coin <= remaining) {
                    best = Math.min(best, fewest(remaining - coin, coins, memo, unreachable) + 1);
                }
            }
            memo[remaining] = best;
        }
        return memo[remaining];
    }
}
