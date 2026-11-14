class Solution {
    fun missingNumber(nums: IntArray): Int {
        val n = nums.size.toLong()
        // n * (n + 1) / 2 reaches 5 * 10^9 for n = 10^5: it must be computed in Long.
        val expected = n * (n + 1) / 2
        return (expected - nums.sumOf { it.toLong() }).toInt()
    }
}
