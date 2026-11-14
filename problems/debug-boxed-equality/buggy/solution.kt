// Debug: Boxed Integer Equality. Some tests fail: find the bug and fix it.
class Solution {
    fun changedSkus(before: List<Int>, after: List<Int>): List<Int> =
        after.indices.filter { before.getOrNull(it) !== after.getOrNull(it) }
}
