class Solution {
    fun maxSubArray(nums: IntArray): Int {
        // endingHere is the best sum of a subarray that ends at the current index.
        var endingHere = nums[0]
        var best = nums[0]
        for (index in 1 until nums.size) {
            endingHere = maxOf(nums[index], endingHere + nums[index])
            best = maxOf(best, endingHere)
        }
        return best
    }
}
