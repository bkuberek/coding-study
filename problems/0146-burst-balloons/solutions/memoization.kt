class Solution {
    fun maxCoins(nums: IntArray): Int {
        // Pad with the virtual balloons of value 1 at both ends.
        val values = intArrayOf(1, *nums, 1)
        // best[left][right] caches the most coins from bursting every balloon strictly between
        // left and right, while those two are still standing; -1 is unknown.
        val best = Array(values.size) { IntArray(values.size) { -1 } }

        fun solve(left: Int, right: Int): Int {
            if (right - left < 2) return 0
            if (best[left][right] < 0) {
                // The balloon burst last between them has exactly left and right as neighbors.
                best[left][right] = (left + 1 until right).maxOf { last ->
                    solve(left, last) + values[left] * values[last] * values[right] + solve(last, right)
                }
            }
            return best[left][right]
        }

        return solve(0, values.size - 1)
    }
}
