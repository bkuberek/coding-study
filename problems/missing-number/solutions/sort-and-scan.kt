class Solution {
    fun missingNumber(nums: IntArray): Int {
        val sorted = nums.sortedArray()
        // In the sorted array, value i sits at index i until the gap.
        return sorted.indices.firstOrNull { sorted[it] != it } ?: nums.size
    }
}
