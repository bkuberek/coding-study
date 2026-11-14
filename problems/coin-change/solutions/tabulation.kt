class Solution {
    fun coinChange(coins: IntArray, amount: Int): Int {
        // fewest[x] is the fewest coins that pay x exactly; amount + 1 means "cannot be paid".
        val unreachable = amount + 1
        val fewest = IntArray(amount + 1) { unreachable }
        fewest[0] = 0
        for (x in 1..amount) {
            for (coin in coins) {
                if (coin <= x && fewest[x - coin] + 1 < fewest[x]) {
                    fewest[x] = fewest[x - coin] + 1
                }
            }
        }
        return if (fewest[amount] == unreachable) -1 else fewest[amount]
    }
}
