class Solution {
    fun maxProduct(nums: IntArray): Int {
        // Within a zero-free run, the best product is a prefix or a suffix of the run, so the
        // running products from both ends (restarted after each zero) cover every candidate.
        var best = nums.max()
        var fromLeft = 1
        var fromRight = 1
        val n = nums.size
        for (i in 0 until n) {
            fromLeft = (if (fromLeft == 0) 1 else fromLeft) * nums[i]
            fromRight = (if (fromRight == 0) 1 else fromRight) * nums[n - 1 - i]
            best = maxOf(best, fromLeft, fromRight)
        }
        return best
    }
}
