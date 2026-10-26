class Solution {
    fun maxSlidingWindow(nums: IntArray, k: Int): IntArray =
        IntArray(nums.size - k + 1) { start ->
            var best = nums[start]
            for (i in start + 1 until start + k) {
                best = maxOf(best, nums[i])
            }
            best
        }
}
