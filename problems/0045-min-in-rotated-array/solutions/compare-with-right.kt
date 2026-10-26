class Solution {
    fun findMin(nums: IntArray): Int {
        // Invariant: the index of the minimum lies in [low, high].
        var low = 0
        var high = nums.lastIndex
        while (low < high) {
            val middle = (low + high) ushr 1
            if (nums[middle] > nums[high]) low = middle + 1 else high = middle
        }
        return nums[low]
    }
}
