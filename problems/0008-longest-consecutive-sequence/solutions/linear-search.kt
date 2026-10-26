class Solution {
    fun longestConsecutive(nums: IntArray): Int {
        var longest = 0
        for ((i, value) in nums.withIndex()) {
            // `in` (contains) and indexOf on an IntArray are linear scans: O(n) per check.
            if (value - 1 in nums) {
                continue
            }
            if (nums.indexOf(value) < i) {
                continue // an earlier copy of this start already counted its run
            }
            var length = 1
            while (value + length in nums) {
                length++
            }
            longest = maxOf(longest, length)
        }
        return longest
    }
}
