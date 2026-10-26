class Solution {
    fun maxProfit(prices: IntArray): Int {
        var cheapest = prices[0]
        var best = 0
        for (price in prices) {
            // Selling today, the best purchase is the cheapest earlier day (or today: profit 0).
            best = maxOf(best, price - cheapest)
            cheapest = minOf(cheapest, price)
        }
        return best
    }
}
