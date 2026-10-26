class Solution {
    fun majorityElement(nums: IntArray): Int {
        val ordered = nums.sortedArray()
        return ordered[ordered.size / 2]
    }
}
