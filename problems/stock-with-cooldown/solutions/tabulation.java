import java.util.*;

public class Solution {
    public int maxProfit(int[] prices) {
        int n = prices.length;
        // Best profit at the end of day i when:
        //   hold[i]: a share is held; sold[i]: a share was sold on day i;
        //   rest[i]: no share is held and none was sold on day i (free to buy tomorrow).
        int[] hold = new int[n];
        int[] sold = new int[n];
        int[] rest = new int[n];
        hold[0] = -prices[0];
        for (int i = 1; i < n; i++) {
            hold[i] = Math.max(hold[i - 1], rest[i - 1] - prices[i]);
            sold[i] = hold[i - 1] + prices[i];
            rest[i] = Math.max(rest[i - 1], sold[i - 1]);
        }
        return Math.max(sold[n - 1], rest[n - 1]);
    }
}
