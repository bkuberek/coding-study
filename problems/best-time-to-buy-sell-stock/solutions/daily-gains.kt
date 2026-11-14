class Solution {
    fun maxProfit(prices: IntArray): Int {
        // A trade from day i to day j earns the sum of the daily changes between them, so the
        // answer is the best sum of a run of consecutive changes (Kadane), or 0.
        var best = 0
        var endingHere = 0
        for (day in 1 until prices.size) {
            endingHere = maxOf(0, endingHere + prices[day] - prices[day - 1])
            best = maxOf(best, endingHere)
        }
        return best
    }
}
