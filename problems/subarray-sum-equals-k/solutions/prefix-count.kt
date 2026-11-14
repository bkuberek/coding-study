class Solution {
    fun subarraySum(nums: IntArray, k: Int): Int {
        // seen maps a prefix sum to how many prefixes so far have it; the empty prefix sums to 0.
        val seen = HashMap<Int, Int>()
        seen[0] = 1
        var total = 0
        var count = 0
        for (value in nums) {
            total += value
            count += seen[total - k] ?: 0
            seen[total] = (seen[total] ?: 0) + 1
        }
        return count
    }
}
