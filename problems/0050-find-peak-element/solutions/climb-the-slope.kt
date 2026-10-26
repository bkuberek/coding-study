class Solution {
    fun findPeakElement(nums: IntArray): Int {
        // Invariant: some peak of the whole array lies in [low, high].
        var low = 0
        var high = nums.lastIndex
        while (low < high) {
            val middle = (low + high) ushr 1
            if (nums[middle] < nums[middle + 1]) low = middle + 1 else high = middle
        }
        return low
    }
}
