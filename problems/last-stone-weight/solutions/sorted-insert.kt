class Solution {
    fun lastStoneWeight(stones: IntArray): Int {
        val remaining = stones.sorted().toMutableList()
        while (remaining.size > 1) {
            val heaviest = remaining.removeAt(remaining.lastIndex)
            val second = remaining.removeAt(remaining.lastIndex)
            if (heaviest != second) {
                val stone = heaviest - second
                // binarySearch returns -(insertion point) - 1 when the value is absent.
                val index = remaining.binarySearch(stone)
                remaining.add(if (index >= 0) index else -index - 1, stone)
            }
        }
        return remaining.firstOrNull() ?: 0
    }
}
