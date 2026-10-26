class Solution {
    fun threeSum(nums: IntArray): List<List<Int>> {
        val values = nums.sortedArray()
        val n = values.size
        val triples = mutableListOf<List<Int>>()
        for (i in 0 until n - 2) {
            if (i > 0 && values[i] == values[i - 1]) continue
            for (j in i + 1 until n - 1) {
                if (j > i + 1 && values[j] == values[j - 1]) continue
                val third = -values[i] - values[j]
                if ((j + 1 until n).any { k -> values[k] == third }) {
                    triples.add(listOf(values[i], values[j], third))
                }
            }
        }
        return triples
    }
}
