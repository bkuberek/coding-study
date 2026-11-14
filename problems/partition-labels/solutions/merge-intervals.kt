class Solution {
    fun partitionLabels(s: String): IntArray {
        // Each letter occupies the span from its first to its last copy. LinkedHashMap keeps
        // insertion order, so letters come by first occurrence, which sorts the spans by start.
        val spans = LinkedHashMap<Char, IntArray>()
        for ((index, letter) in s.withIndex()) {
            spans.getOrPut(letter) { intArrayOf(index, index) }[1] = index
        }
        val sizes = mutableListOf<Int>()
        var pieceStart = 0
        var pieceEnd = -1
        for ((first, last) in spans.values) {
            if (first > pieceEnd) {
                if (pieceEnd >= 0) sizes.add(pieceEnd - pieceStart + 1)
                pieceStart = first
            }
            pieceEnd = maxOf(pieceEnd, last)
        }
        sizes.add(pieceEnd - pieceStart + 1)
        return sizes.toIntArray()
    }
}
