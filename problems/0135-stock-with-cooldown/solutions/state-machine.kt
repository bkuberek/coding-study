class Solution {
    fun maxProfit(prices: IntArray): Int {
        // The three end-of-day states of the previous day: holding a share, just sold, resting.
        var hold = -prices[0]
        var sold = 0
        var rest = 0
        for (i in 1 until prices.size) {
            val nextHold = maxOf(hold, rest - prices[i])
            val nextSold = hold + prices[i]
            val nextRest = maxOf(rest, sold)
            hold = nextHold
            sold = nextSold
            rest = nextRest
        }
        return maxOf(sold, rest)
    }
}
