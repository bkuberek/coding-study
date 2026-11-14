import java.util.*;

public class Solution {
    public int maxProfit(int[] prices) {
        // The three end-of-day states of the previous day: holding a share, just sold, resting.
        int hold = -prices[0];
        int sold = 0;
        int rest = 0;
        for (int i = 1; i < prices.length; i++) {
            int nextHold = Math.max(hold, rest - prices[i]);
            int nextSold = hold + prices[i];
            int nextRest = Math.max(rest, sold);
            hold = nextHold;
            sold = nextSold;
            rest = nextRest;
        }
        return Math.max(sold, rest);
    }
}
