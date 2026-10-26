class Solution {
    fun threeSum(nums: IntArray): List<List<Int>> {
        val values = nums.sortedArray()
        val n = values.size
        val triples = mutableListOf<List<Int>>()
        for (i in 0 until n - 2) {
            if (values[i] > 0) break
            if (i > 0 && values[i] == values[i - 1]) continue
            var left = i + 1
            var right = n - 1
            while (left < right) {
                val total = values[i] + values[left] + values[right]
                when {
                    total < 0 -> left++
                    total > 0 -> right--
                    else -> {
                        triples.add(listOf(values[i], values[left], values[right]))
                        left++
                        right--
                        while (left < right && values[left] == values[left - 1]) left++
                    }
                }
            }
        }
        return triples
    }
}
