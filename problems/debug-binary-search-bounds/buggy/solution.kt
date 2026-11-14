// Debug: Binary Search Bounds. Some tests fail: find the bug and fix it.
class Solution {
    fun search(nums: IntArray, target: Int): Int {
        var lo = 0
        var hi = nums.size - 1
        while (lo < hi) {
            val mid = (lo + hi) / 2
            when {
                nums[mid] == target -> return mid
                nums[mid] < target -> lo = mid + 1
                else -> hi = mid
            }
        }
        return -1
    }
}
