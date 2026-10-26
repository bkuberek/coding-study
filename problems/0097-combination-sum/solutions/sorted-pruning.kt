class Solution {
    fun combinationSum(candidates: IntArray, target: Int): List<List<Int>> {
        val ordered = candidates.sorted()
        val result = mutableListOf<List<Int>>()
        val chosen = ArrayList<Int>()

        // Values are added in non-decreasing order, so each combination is built once.
        fun extend(start: Int, remaining: Int) {
            if (remaining == 0) {
                result.add(chosen.toList())
                return
            }
            for (i in start until ordered.size) {
                val value = ordered[i]
                if (value > remaining) break
                chosen.add(value)
                extend(i, remaining - value)
                chosen.removeAt(chosen.size - 1)
            }
        }

        extend(0, target)
        return result
    }
}
