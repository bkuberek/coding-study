class Solution {
    fun minDistance(word1: String, word2: String): Int {
        // cost[i][j] is the distance between the prefixes word1[:i] and word2[:j]. Turning a prefix
        // into the empty word takes one deletion per character, and the reverse one insertion.
        val cost = Array(word1.length + 1) { i -> IntArray(word2.length + 1) { j -> if (i == 0) j else 0 } }
        for (i in 1..word1.length) {
            cost[i][0] = i
            for (j in 1..word2.length) {
                cost[i][j] = if (word1[i - 1] == word2[j - 1]) {
                    cost[i - 1][j - 1]
                } else {
                    1 + minOf(cost[i - 1][j], cost[i][j - 1], cost[i - 1][j - 1])
                }
            }
        }
        return cost[word1.length][word2.length]
    }
}
