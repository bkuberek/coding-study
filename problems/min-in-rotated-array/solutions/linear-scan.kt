class Solution {
    fun findMin(nums: IntArray): Int {
        var smallest = nums[0]
        for (value in nums) {
            if (value < smallest) {
                smallest = value
            }
        }
        return smallest
    }
}
