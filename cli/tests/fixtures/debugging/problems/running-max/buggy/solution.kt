// Running Maximum (debugging): some tests fail. Find the bug and fix it.
class Solution {
    fun runningMax(nums: IntArray): IntArray {
        var best = 0
        return IntArray(nums.size) { i ->
            best = maxOf(best, nums[i])
            best
        }
    }
}
