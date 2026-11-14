class Solution {
    fun productExceptSelf(nums: IntArray): IntArray =
        IntArray(nums.size) { i ->
            var product = 1
            for (j in nums.indices) {
                if (j != i) {
                    product *= nums[j]
                }
            }
            product
        }
}
