class Solution {
    fun majorityElement(nums: IntArray): Int {
        var candidate = nums[0]
        var votes = 0
        for (value in nums) {
            if (votes == 0) {
                candidate = value
            }
            votes += if (value == candidate) 1 else -1
        }
        return candidate
    }
}
