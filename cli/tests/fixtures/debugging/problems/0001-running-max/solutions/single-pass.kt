class Solution {
    fun runningMax(nums: IntArray): IntArray {
        var best = nums[0]
        return IntArray(nums.size) { i ->
            best = maxOf(best, nums[i])
            best
        }
    }
}
