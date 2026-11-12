public class Solution {
    public int[] pricesAfterRebate(int[] prices) {
        int[] paid = prices.clone();
        // Slots still waiting for a rebate, as a stack in a plain array: waiting[0 .. size).
        int[] waiting = new int[prices.length];
        int size = 0;
        for (int slot = 0; slot < prices.length; slot++) {
            while (size > 0 && prices[waiting[size - 1]] >= prices[slot]) {
                int earlier = waiting[--size];
                paid[earlier] = prices[earlier] - prices[slot];
            }
            waiting[size++] = slot;
        }
        return paid;
    }
}
