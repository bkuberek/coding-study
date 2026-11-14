class Solution {
    fun changedSkus(before: List<Int>, after: List<Int>): List<Int> =
        after.indices.filter { before.getOrNull(it) != after[it] }
}
