class Solution {
    fun combinationSum2(candidates: IntArray, target: Int): List<List<Int>> {
        val ordered = candidates.sorted()
        val result = mutableListOf<List<Int>>()
        val chosen = ArrayList<Int>()

        fun extend(start: Int, remaining: Int) {
            if (remaining == 0) {
                result.add(chosen.toList())
                return
            }
            for (i in start until ordered.size) {
                val value = ordered[i]
                if (value > remaining) break
                // A second copy at the same level would rebuild the first copy's combinations.
                if (i > start && value == ordered[i - 1]) continue
                chosen.add(value)
                extend(i + 1, remaining - value)
                chosen.removeAt(chosen.size - 1)
            }
        }

        extend(0, target)
        return result
    }
}
