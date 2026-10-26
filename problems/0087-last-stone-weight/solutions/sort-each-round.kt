class Solution {
    fun lastStoneWeight(stones: IntArray): Int {
        val remaining = stones.toMutableList()
        while (remaining.size > 1) {
            remaining.sort()
            val heaviest = remaining.removeAt(remaining.lastIndex)
            val second = remaining.removeAt(remaining.lastIndex)
            if (heaviest != second) remaining.add(heaviest - second)
        }
        return remaining.firstOrNull() ?: 0
    }
}
