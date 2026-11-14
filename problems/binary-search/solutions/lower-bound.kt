class Solution {
    fun search(nums: IntArray, target: Int): Int {
        // Find the first index whose value is >= target, in the half-open range [low, high).
        var low = 0
        var high = nums.size
        while (low < high) {
            val middle = (low + high) ushr 1
            if (nums[middle] < target) {
                low = middle + 1
            } else {
                high = middle
            }
        }
        return if (low < nums.size && nums[low] == target) low else -1
    }
}
