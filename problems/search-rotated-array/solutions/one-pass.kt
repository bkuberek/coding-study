class Solution {
    fun search(nums: IntArray, target: Int): Int {
        var low = 0
        var high = nums.size - 1
        while (low <= high) {
            val middle = (low + high) ushr 1
            if (nums[middle] == target) {
                return middle
            }
            val leftSorted = nums[low] <= nums[middle]
            val inSortedHalf = if (leftSorted) {
                target >= nums[low] && target < nums[middle]
            } else {
                target > nums[middle] && target <= nums[high]
            }
            // Keep the sorted half when it can hold target, the other half otherwise.
            if (leftSorted == inSortedHalf) high = middle - 1 else low = middle + 1
        }
        return -1
    }
}
