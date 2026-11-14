class Solution {
    fun topKFrequent(nums: IntArray, k: Int): IntArray {
        val counts = HashMap<Int, Int>()
        for (value in nums) {
            counts[value] = counts.getOrDefault(value, 0) + 1
        }
        // buckets[c] holds the values that occur exactly c times; no count exceeds nums.size.
        val buckets = Array(nums.size + 1) { mutableListOf<Int>() }
        for ((value, count) in counts) {
            buckets[count].add(value)
        }
        val answer = ArrayList<Int>(k)
        for (count in nums.size downTo 1) {
            for (value in buckets[count]) {
                answer.add(value)
                if (answer.size == k) {
                    return answer.toIntArray()
                }
            }
        }
        return answer.toIntArray()
    }
}
