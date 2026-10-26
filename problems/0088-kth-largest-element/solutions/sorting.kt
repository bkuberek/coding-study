class Solution {
    fun findKthLargest(nums: IntArray, k: Int): Int = nums.sortedArray()[nums.size - k]
}
