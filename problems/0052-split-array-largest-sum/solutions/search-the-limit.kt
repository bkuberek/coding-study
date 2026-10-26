class Solution {
    fun splitArray(nums: IntArray, k: Int): Int {
        // Feasibility only improves as the limit grows: find the smallest feasible limit.
        var low = nums.max()
        var high = nums.sum()
        while (low < high) {
            val limit = low + (high - low) / 2
            if (piecesNeeded(nums, limit) <= k) high = limit else low = limit + 1
        }
        return low
    }

    // Greedy: extend the current piece while it fits under the limit.
    private fun piecesNeeded(nums: IntArray, limit: Int): Int {
        var pieces = 1
        var running = 0
        for (value in nums) {
            if (running + value > limit) {
                pieces++
                running = value
            } else {
                running += value
            }
        }
        return pieces
    }
}
