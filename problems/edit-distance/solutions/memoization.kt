class Solution {
    fun minDistance(word1: String, word2: String): Int {
        // cost[i][j] caches the distance between the suffixes word1[i:] and word2[j:]; -1 is unknown.
        val cost = Array(word1.length + 1) { IntArray(word2.length + 1) { -1 } }

        fun solve(i: Int, j: Int): Int {
            if (i == word1.length) return word2.length - j // insert the rest of word2
            if (j == word2.length) return word1.length - i // delete the rest of word1
            if (cost[i][j] < 0) {
                cost[i][j] = if (word1[i] == word2[j]) {
                    solve(i + 1, j + 1)
                } else {
                    1 + minOf(solve(i + 1, j), solve(i, j + 1), solve(i + 1, j + 1))
                }
            }
            return cost[i][j]
        }

        return solve(0, 0)
    }
}
