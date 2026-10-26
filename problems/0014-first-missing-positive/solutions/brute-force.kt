class Solution {
    fun firstMissingPositive(nums: IntArray): Int {
        var candidate = 1
        // `in` on an IntArray is a linear scan: O(n) per candidate.
        while (candidate in nums) {
            candidate++
        }
        return candidate
    }
}
