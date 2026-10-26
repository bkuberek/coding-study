class Solution {
    fun moveZeroes(nums: IntArray) {
        var write = 0
        for (read in nums.indices) {
            if (nums[read] != 0) {
                nums[write] = nums[read].also { nums[read] = nums[write] }
                write++
            }
        }
    }
}
