class Solution {
    fun search(nums: IntArray, target: Int): Int {
        val pivot = indexOfMinimum(nums)
        val last = nums.size - 1
        return if (target in nums[pivot]..nums[last]) {
            binarySearch(nums, target, pivot, last)
        } else {
            binarySearch(nums, target, 0, pivot - 1)
        }
    }

    private fun indexOfMinimum(nums: IntArray): Int {
        var low = 0
        var high = nums.size - 1
        while (low < high) {
            val middle = (low + high) ushr 1
            if (nums[middle] > nums[high]) low = middle + 1 else high = middle
        }
        return low
    }

    private fun binarySearch(nums: IntArray, target: Int, from: Int, to: Int): Int {
        var low = from
        var high = to
        while (low <= high) {
            val middle = (low + high) ushr 1
            when {
                nums[middle] == target -> return middle
                nums[middle] < target -> low = middle + 1
                else -> high = middle - 1
            }
        }
        return -1
    }
}
