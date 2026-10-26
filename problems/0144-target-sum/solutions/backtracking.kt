class Solution {
    fun findTargetSumWays(nums: IntArray, target: Int): Int {
        fun count(index: Int, total: Int): Int {
            if (index == nums.size) return if (total == target) 1 else 0
            // Give nums[index] a plus sign, then a minus sign.
            return count(index + 1, total + nums[index]) + count(index + 1, total - nums[index])
        }

        return count(0, 0)
    }
}
