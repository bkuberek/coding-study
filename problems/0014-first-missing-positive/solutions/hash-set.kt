class Solution {
    fun firstMissingPositive(nums: IntArray): Int {
        val present = nums.toHashSet()
        // The answer is at most nums.size + 1, so this loop runs at most n + 1 times.
        var candidate = 1
        while (candidate in present) {
            candidate++
        }
        return candidate
    }
}
