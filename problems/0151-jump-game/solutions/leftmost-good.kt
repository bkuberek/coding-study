class Solution {
    fun canJump(nums: IntArray): Boolean {
        var goal = nums.size - 1 // the leftmost index known to reach the last index
        for (i in nums.size - 2 downTo 0) {
            if (i + nums[i] >= goal) goal = i
        }
        return goal == 0
    }
}
