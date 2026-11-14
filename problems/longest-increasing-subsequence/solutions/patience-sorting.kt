class Solution {
    fun lengthOfLIS(nums: IntArray): Int {
        // tails[0 until size] holds, for each length L, the smallest last value of an
        // increasing subsequence of length L seen so far; it is strictly increasing.
        val tails = IntArray(nums.size)
        var size = 0
        for (value in nums) {
            var position = tails.binarySearch(value, 0, size)
            if (position < 0) position = -(position + 1)
            tails[position] = value
            if (position == size) size++
        }
        return size
    }
}
