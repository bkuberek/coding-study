class Solution {
    fun maxProduct(nums: IntArray): Int {
        // largest and smallest are the extreme products of subarrays that end at the current index.
        var largest = nums[0]
        var smallest = nums[0]
        var best = nums[0]
        for (i in 1 until nums.size) {
            val value = nums[i]
            val extendLargest = largest * value
            val extendSmallest = smallest * value
            largest = maxOf(value, extendLargest, extendSmallest)
            smallest = minOf(value, extendLargest, extendSmallest)
            best = maxOf(best, largest)
        }
        return best
    }
}
