class Solution {
    fun change(amount: Int, coins: IntArray): Int {
        // After processing a prefix of the coins, ways[total] counts the combinations for `total`
        // that use only those coins.
        val ways = IntArray(amount + 1)
        ways[0] = 1
        for (coin in coins) {
            // Increasing totals: ways[total - coin] already allows this coin, so it can repeat.
            for (total in coin..amount) {
                ways[total] += ways[total - coin]
            }
        }
        return ways[amount]
    }
}
