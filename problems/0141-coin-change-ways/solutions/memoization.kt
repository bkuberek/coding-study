class Solution {
    fun change(amount: Int, coins: IntArray): Int {
        // ways[i][total] caches the combinations for `total` using coins[i:]; -1 is unknown.
        val ways = Array(coins.size) { IntArray(amount + 1) { -1 } }

        fun count(i: Int, total: Int): Int {
            if (total == 0) return 1
            if (i == coins.size) return 0
            if (ways[i][total] < 0) {
                // Either no coin of value coins[i] is used, or at least one is.
                val skip = count(i + 1, total)
                val use = if (coins[i] <= total) count(i, total - coins[i]) else 0
                ways[i][total] = skip + use
            }
            return ways[i][total]
        }

        return count(0, amount)
    }
}
