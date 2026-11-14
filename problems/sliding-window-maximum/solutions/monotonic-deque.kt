class Solution {
    fun maxSlidingWindow(nums: IntArray, k: Int): IntArray {
        val candidates = ArrayDeque<Int>()
        val maxima = IntArray(nums.size - k + 1)
        for (right in nums.indices) {
            while (candidates.isNotEmpty() && nums[candidates.last()] <= nums[right]) {
                candidates.removeLast()
            }
            candidates.addLast(right)
            if (candidates.first() <= right - k) candidates.removeFirst()
            if (right >= k - 1) maxima[right - k + 1] = nums[candidates.first()]
        }
        return maxima
    }
}
