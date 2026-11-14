class Solution {
    fun minSubArrayLen(target: Int, nums: IntArray): Int {
        val n = nums.size
        val prefix = IntArray(n + 1)
        for (i in nums.indices) prefix[i + 1] = prefix[i] + nums[i]
        var best = 0
        for (start in 0 until n) {
            val found = prefix.binarySearch(prefix[start] + target, fromIndex = start + 1)
            val end = if (found >= 0) found else -found - 1
            if (end <= n && (best == 0 || end - start < best)) best = end - start
        }
        return best
    }
}
