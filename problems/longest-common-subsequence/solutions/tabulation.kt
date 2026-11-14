class Solution {
    fun longestCommonSubsequence(text1: String, text2: String): Int {
        // best[i][j] is the answer for the prefixes text1[:i] and text2[:j]; row and column 0
        // stand for an empty prefix.
        val best = Array(text1.length + 1) { IntArray(text2.length + 1) }
        for (i in 1..text1.length) {
            for (j in 1..text2.length) {
                best[i][j] = if (text1[i - 1] == text2[j - 1]) {
                    best[i - 1][j - 1] + 1
                } else {
                    maxOf(best[i - 1][j], best[i][j - 1])
                }
            }
        }
        return best[text1.length][text2.length]
    }
}
