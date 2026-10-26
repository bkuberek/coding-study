class Solution {
    fun longestConsecutive(nums: IntArray): Int {
        if (nums.isEmpty()) {
            return 0
        }
        val ordered = nums.sortedArray()
        var longest = 1
        var current = 1
        for (i in 1 until ordered.size) {
            if (ordered[i] == ordered[i - 1]) {
                continue
            }
            current = if (ordered[i] == ordered[i - 1] + 1) current + 1 else 1
            longest = maxOf(longest, current)
        }
        return longest
    }
}
