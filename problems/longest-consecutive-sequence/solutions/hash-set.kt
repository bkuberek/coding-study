class Solution {
    fun longestConsecutive(nums: IntArray): Int {
        val present = nums.toHashSet()
        var longest = 0
        for (value in present) {
            if (value - 1 in present) {
                continue
            }
            var end = value + 1
            while (end in present) {
                end++
            }
            longest = maxOf(longest, end - value)
        }
        return longest
    }
}
