class Solution {
    fun splitArray(nums: IntArray, k: Int): Int {
        val n = nums.size
        val prefix = IntArray(n + 1)
        for (i in nums.indices) {
            prefix[i + 1] = prefix[i] + nums[i]
        }
        // best[i]: the smallest cost of cutting the first i values into the current number of pieces.
        var best = prefix.copyOf()
        for (pieces in 2..k) {
            val previous = best
            best = IntArray(n + 1) { end ->
                if (end < pieces) {
                    0
                } else {
                    (pieces - 1 until end).minOf { cut -> maxOf(previous[cut], prefix[end] - prefix[cut]) }
                }
            }
        }
        return best[n]
    }
}
