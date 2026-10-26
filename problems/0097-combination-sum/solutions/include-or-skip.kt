class Solution {
    fun combinationSum(candidates: IntArray, target: Int): List<List<Int>> {
        val result = mutableListOf<List<Int>>()
        val chosen = ArrayList<Int>()

        fun explore(index: Int, remaining: Int) {
            if (remaining == 0) {
                result.add(chosen.toList())
                return
            }
            if (remaining < 0 || index == candidates.size) return
            // Use candidates[index] once more and stay on it, since it may repeat.
            chosen.add(candidates[index])
            explore(index, remaining - candidates[index])
            chosen.removeAt(chosen.size - 1)
            // Or never use it again.
            explore(index + 1, remaining)
        }

        explore(0, target)
        return result
    }
}
