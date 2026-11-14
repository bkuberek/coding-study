class Solution {
    fun majorityElement(nums: IntArray): Int {
        val half = nums.size / 2
        for (candidate in nums) {
            if (nums.count { it == candidate } > half) {
                return candidate
            }
        }
        throw IllegalArgumentException("no majority element")
    }
}
