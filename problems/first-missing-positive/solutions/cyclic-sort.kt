class Solution {
    fun firstMissingPositive(nums: IntArray): Int {
        val n = nums.size
        for (i in 0 until n) {
            // Swap nums[i] to its home index nums[i] - 1 until the value here has no home in
            // range or its home already holds it. Every swap settles one value for good.
            while (nums[i] in 1..n && nums[nums[i] - 1] != nums[i]) {
                val home = nums[i] - 1
                val displaced = nums[home]
                nums[home] = nums[i]
                nums[i] = displaced
            }
        }
        for (i in 0 until n) {
            if (nums[i] != i + 1) {
                return i + 1
            }
        }
        return n + 1
    }
}
