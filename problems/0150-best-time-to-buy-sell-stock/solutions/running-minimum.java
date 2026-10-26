import java.util.*;

public class Solution {
    public int maxProfit(int[] prices) {
        int cheapest = prices[0];
        int best = 0;
        for (int price : prices) {
            // Selling today, the best purchase is the cheapest earlier day (or today: profit 0).
            best = Math.max(best, price - cheapest);
            cheapest = Math.min(cheapest, price);
        }
        return best;
    }
}
