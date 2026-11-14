class Solution {
    fun singleNumber(nums: IntArray): Int {
        val counts = nums.asIterable().groupingBy { it }.eachCount()
        return counts.entries.first { it.value == 1 }.key
    }
}
