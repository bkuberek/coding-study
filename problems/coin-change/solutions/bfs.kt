class Solution {
    fun coinChange(coins: IntArray, amount: Int): Int {
        // Remainders are nodes and paying one coin is an edge; the first level that reaches 0
        // is the fewest number of coins.
        val seen = BooleanArray(amount + 1)
        seen[amount] = true
        var level = listOf(amount)
        var coinsUsed = 0
        while (level.isNotEmpty()) {
            if (seen[0]) return coinsUsed
            val nextLevel = mutableListOf<Int>()
            for (remaining in level) {
                for (coin in coins) {
                    val rest = remaining - coin
                    if (rest >= 0 && !seen[rest]) {
                        seen[rest] = true
                        nextLevel.add(rest)
                    }
                }
            }
            level = nextLevel
            coinsUsed++
        }
        return -1
    }
}
