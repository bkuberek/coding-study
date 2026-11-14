class Solution {
    fun search(nums: IntArray, target: Int): Int {
        // Invariant: if target is in nums, its index lies in [low, high].
        var low = 0
        var high = nums.size - 1
        while (low <= high) {
            val middle = low + (high - low) / 2
            when {
                nums[middle] == target -> return middle
                nums[middle] < target -> low = middle + 1
                else -> high = middle - 1
            }
        }
        return -1
    }
}
