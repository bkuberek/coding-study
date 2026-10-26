class Solution {
    fun searchRange(nums: IntArray, target: Int): IntArray {
        val hit = nums.binarySearch(target)
        if (hit < 0) {
            return intArrayOf(-1, -1)
        }
        var first = hit
        var last = hit
        while (first > 0 && nums[first - 1] == target) first--
        while (last < nums.lastIndex && nums[last + 1] == target) last++
        return intArrayOf(first, last)
    }
}
