class Solution {
    fun searchInsert(nums: IntArray, target: Int): Int {
        var low = 0
        var high = nums.size // the answer lies in [low, high]
        while (low < high) {
            val middle = low + (high - low) / 2
            if (nums[middle] < target) {
                low = middle + 1
            } else {
                high = middle
            }
        }
        return low
    }
}
