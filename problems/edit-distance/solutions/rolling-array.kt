class Solution {
    fun minDistance(word1: String, word2: String): Int {
        // The distance is symmetric (insertions and deletions swap roles), so let the rows run
        // along the shorter word.
        val (longer, shorter) = if (word1.length >= word2.length) word1 to word2 else word2 to word1
        // previous[j] is the distance between longer[:i - 1] and shorter[:j].
        var previous = IntArray(shorter.length + 1) { it }
        var current = IntArray(shorter.length + 1)
        for ((index, character) in longer.withIndex()) {
            current[0] = index + 1
            for (j in 1..shorter.length) {
                current[j] = if (character == shorter[j - 1]) {
                    previous[j - 1]
                } else {
                    1 + minOf(previous[j], current[j - 1], previous[j - 1])
                }
            }
            previous = current.also { current = previous }
        }
        return previous[shorter.length]
    }
}
