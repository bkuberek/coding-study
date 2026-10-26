class Solution {
    fun longestCommonSubsequence(text1: String, text2: String): Int {
        // best[i][j] caches the answer for the suffixes text1[i:] and text2[j:]; -1 is unknown.
        val best = Array(text1.length) { IntArray(text2.length) { -1 } }

        fun solve(i: Int, j: Int): Int {
            if (i == text1.length || j == text2.length) return 0
            if (best[i][j] < 0) {
                best[i][j] = if (text1[i] == text2[j]) {
                    1 + solve(i + 1, j + 1)
                } else {
                    maxOf(solve(i + 1, j), solve(i, j + 1))
                }
            }
            return best[i][j]
        }

        return solve(0, 0)
    }
}
