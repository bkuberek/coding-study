class Solution {
    fun longestOnes(nums: IntArray, k: Int): Int {
        var left = 0
        var flipsLeft = k
        for (value in nums) {
            if (value == 0) flipsLeft--
            if (flipsLeft < 0 && nums[left++] == 0) flipsLeft++
        }
        return nums.size - left
    }
}
