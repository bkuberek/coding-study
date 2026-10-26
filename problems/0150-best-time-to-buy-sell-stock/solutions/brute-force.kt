class Solution {
    fun maxProfit(prices: IntArray): Int {
        var best = 0
        for (buy in prices.indices) {
            for (sell in buy + 1 until prices.size) {
                best = maxOf(best, prices[sell] - prices[buy])
            }
        }
        return best
    }
}
