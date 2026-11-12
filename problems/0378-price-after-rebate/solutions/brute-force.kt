class Solution {
    fun pricesAfterRebate(prices: IntArray): IntArray {
        val paid = prices.copyOf()
        for (slot in prices.indices) {
            for (later in slot + 1 until prices.size) {
                if (prices[later] <= prices[slot]) {
                    paid[slot] = prices[slot] - prices[later]
                    break
                }
            }
        }
        return paid
    }
}
