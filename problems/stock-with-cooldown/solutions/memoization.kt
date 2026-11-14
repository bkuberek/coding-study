class Solution {
    fun maxProfit(prices: IntArray): Int {
        val n = prices.size
        // memo[holding][day] is the most profit from `day` on, or -1 when unknown.
        val memo = Array(2) { IntArray(n) { -1 } }

        fun best(day: Int, holding: Int): Int {
            if (day >= n) return 0
            if (memo[holding][day] == -1) {
                val wait = best(day + 1, holding)
                // Selling today forces tomorrow to be a cooldown day, so resume on day + 2.
                val act = if (holding == 1) {
                    prices[day] + best(day + 2, 0)
                } else {
                    -prices[day] + best(day + 1, 1)
                }
                memo[holding][day] = maxOf(wait, act)
            }
            return memo[holding][day]
        }

        return best(0, 0)
    }
}
