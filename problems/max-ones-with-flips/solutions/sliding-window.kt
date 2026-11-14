class Solution {
    fun longestOnes(nums: IntArray, k: Int): Int {
        var left = 0
        var zeros = 0
        var best = 0
        for (right in nums.indices) {
            if (nums[right] == 0) zeros++
            while (zeros > k) {
                if (nums[left++] == 0) zeros--
            }
            best = maxOf(best, right - left + 1)
        }
        return best
    }
}
