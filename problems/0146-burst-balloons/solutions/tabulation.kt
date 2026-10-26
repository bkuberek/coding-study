class Solution {
    fun maxCoins(nums: IntArray): Int {
        val values = intArrayOf(1, *nums, 1)
        val size = values.size
        // best[left][right]: most coins from bursting everything strictly between left and right.
        val best = Array(size) { IntArray(size) }
        // An interval only depends on shorter ones, so fill by increasing gap right - left.
        for (gap in 2 until size) {
            for (left in 0 until size - gap) {
                val right = left + gap
                val outer = values[left] * values[right]
                var most = 0
                for (last in left + 1 until right) {
                    most = maxOf(most, best[left][last] + outer * values[last] + best[last][right])
                }
                best[left][right] = most
            }
        }
        return best[0][size - 1]
    }
}
