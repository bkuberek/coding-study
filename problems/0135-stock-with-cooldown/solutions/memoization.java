import java.util.*;

public class Solution {
    private static final int UNKNOWN = -1;

    public int maxProfit(int[] prices) {
        // memo[holding][day] is the most profit from `day` on, or UNKNOWN.
        int[][] memo = new int[2][prices.length];
        for (int[] row : memo) {
            Arrays.fill(row, UNKNOWN);
        }
        return best(0, 0, prices, memo);
    }

    private int best(int day, int holding, int[] prices, int[][] memo) {
        if (day >= prices.length) {
            return 0;
        }
        if (memo[holding][day] == UNKNOWN) {
            int wait = best(day + 1, holding, prices, memo);
            // Selling today forces tomorrow to be a cooldown day, so resume on day + 2.
            int act = holding == 1
                    ? prices[day] + best(day + 2, 0, prices, memo)
                    : -prices[day] + best(day + 1, 1, prices, memo);
            memo[holding][day] = Math.max(wait, act);
        }
        return memo[holding][day];
    }
}
