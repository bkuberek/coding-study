class Solution {
    fun maxProfit(prices: IntArray): Int {
        val n = prices.size
        // Best profit at the end of day i when:
        //   hold[i]: a share is held; sold[i]: a share was sold on day i;
        //   rest[i]: no share is held and none was sold on day i (free to buy tomorrow).
        val hold = IntArray(n)
        val sold = IntArray(n)
        val rest = IntArray(n)
        hold[0] = -prices[0]
        for (i in 1 until n) {
            hold[i] = maxOf(hold[i - 1], rest[i - 1] - prices[i])
            sold[i] = hold[i - 1] + prices[i]
            rest[i] = maxOf(rest[i - 1], sold[i - 1])
        }
        return maxOf(sold[n - 1], rest[n - 1])
    }
}
