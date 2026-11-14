class Solution {
    fun maxProduct(nums: IntArray): Int {
        var best = nums[0]
        for (start in nums.indices) {
            var product = 1
            for (end in start until nums.size) {
                product *= nums[end]
                best = maxOf(best, product)
            }
        }
        return best
    }
}
