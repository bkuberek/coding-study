public class Solution {
    public int[] pricesAfterRebate(int[] prices) {
        int[] paid = prices.clone();
        for (int slot = 0; slot < prices.length; slot++) {
            for (int later = slot + 1; later < prices.length; later++) {
                if (prices[later] <= prices[slot]) {
                    paid[slot] = prices[slot] - prices[later];
                    break;
                }
            }
        }
        return paid;
    }
}
