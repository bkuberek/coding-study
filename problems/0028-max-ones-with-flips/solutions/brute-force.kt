class Solution {
    fun longestOnes(nums: IntArray, k: Int): Int {
        var best = 0
        for (start in nums.indices) {
            var zeros = 0
            var end = start
            while (end < nums.size) {
                if (nums[end] == 0) {
                    if (zeros == k) break
                    zeros++
                }
                end++
            }
            best = maxOf(best, end - start)
        }
        return best
    }
}
