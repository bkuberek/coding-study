class Solution {
    fun topKFrequent(nums: IntArray, k: Int): IntArray =
        nums.asIterable()
            .groupingBy { it }
            .eachCount()
            .entries
            .sortedByDescending { it.value }
            .take(k)
            .map { it.key }
            .toIntArray()
}
