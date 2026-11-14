class Solution {
    fun combinationSum2(candidates: IntArray, target: Int): List<List<Int>> {
        val ordered = candidates.sorted()
        // Values taken in sorted order give each multiset one canonical list; lists compare by content.
        val found = LinkedHashSet<List<Int>>()
        for (mask in 0 until (1 shl ordered.size)) {
            val chosen = ordered.filterIndexed { i, _ -> (mask shr i) and 1 == 1 }
            if (chosen.sum() == target) found.add(chosen)
        }
        return found.toList()
    }
}
