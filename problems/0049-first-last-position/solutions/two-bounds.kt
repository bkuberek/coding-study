class Solution {
    fun searchRange(nums: IntArray, target: Int): IntArray {
        val first = firstIndex(nums) { it >= target }
        if (first == nums.size || nums[first] != target) {
            return intArrayOf(-1, -1)
        }
        return intArrayOf(first, firstIndex(nums) { it > target } - 1)
    }

    // The smallest index whose value satisfies the monotone predicate, or nums.size.
    private inline fun firstIndex(nums: IntArray, isPast: (Int) -> Boolean): Int {
        var low = 0
        var high = nums.size
        while (low < high) {
            val middle = (low + high) ushr 1
            if (isPast(nums[middle])) high = middle else low = middle + 1
        }
        return low
    }
}
