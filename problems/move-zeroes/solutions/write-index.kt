class Solution {
    fun moveZeroes(nums: IntArray) {
        var write = 0
        for (value in nums) {
            if (value != 0) {
                nums[write++] = value
            }
        }
        nums.fill(0, write)
    }
}
