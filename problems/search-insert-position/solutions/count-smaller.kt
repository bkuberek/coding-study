class Solution {
    fun searchInsert(nums: IntArray, target: Int): Int =
        // In a sorted array, target belongs right after every smaller value.
        nums.count { it < target }
}
