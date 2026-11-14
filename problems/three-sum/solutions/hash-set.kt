class Solution {
    fun threeSum(nums: IntArray): List<List<Int>> {
        val values = nums.sortedArray()
        val triples = mutableListOf<List<Int>>()
        for (i in 0 until values.size - 2) {
            if (i > 0 && values[i] == values[i - 1]) continue
            val seen = HashSet<Int>()
            var lastLargest: Int? = null
            for (j in i + 1 until values.size) {
                val middle = -values[i] - values[j]
                if (middle in seen && values[j] != lastLargest) {
                    triples.add(listOf(values[i], middle, values[j]))
                    lastLargest = values[j]
                }
                seen.add(values[j])
            }
        }
        return triples
    }
}
