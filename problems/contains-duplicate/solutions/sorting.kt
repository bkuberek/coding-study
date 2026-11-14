class Solution {
    fun containsDuplicate(nums: IntArray): Boolean {
        // sortedArray returns a sorted copy; nums keeps its order.
        val ordered = nums.sortedArray()
        return (1 until ordered.size).any { ordered[it] == ordered[it - 1] }
    }
}
