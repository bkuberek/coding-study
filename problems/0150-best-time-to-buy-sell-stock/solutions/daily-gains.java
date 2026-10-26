import java.util.*;

public class Solution {
    public int maxProfit(int[] prices) {
        // A trade from day i to day j earns the sum of the daily changes between them, so the
        // answer is the best sum of a run of consecutive changes (Kadane), or 0.
        int best = 0;
        int endingHere = 0;
        for (int day = 1; day < prices.length; day++) {
            endingHere = Math.max(0, endingHere + prices[day] - prices[day - 1]);
            best = Math.max(best, endingHere);
        }
        return best;
    }
}
