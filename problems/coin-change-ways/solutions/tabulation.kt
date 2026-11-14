class Solution {
    fun change(amount: Int, coins: IntArray): Int {
        // ways[i][total] is the number of combinations for `total` using only coins[:i].
        val ways = Array(coins.size + 1) { IntArray(amount + 1) }
        ways[0][0] = 1
        for (i in 1..coins.size) {
            val coin = coins[i - 1]
            for (total in 0..amount) {
                // Combinations without this coin, plus those that use it at least once.
                ways[i][total] = ways[i - 1][total] + if (total >= coin) ways[i][total - coin] else 0
            }
        }
        return ways[coins.size][amount]
    }
}
