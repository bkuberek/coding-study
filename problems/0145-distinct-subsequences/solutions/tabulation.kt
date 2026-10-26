class Solution {
    fun numDistinct(s: String, t: String): Int {
        // ways[i][j] counts the occurrences of t[:j] in s[:i]; the empty t[:0] occurs once.
        val ways = Array(s.length + 1) { IntArray(t.length + 1).also { row -> row[0] = 1 } }
        for (i in 1..s.length) {
            for (j in 1..t.length) {
                // Occurrences that skip s[i - 1], plus those that match it with t[j - 1].
                ways[i][j] = ways[i - 1][j] + if (s[i - 1] == t[j - 1]) ways[i - 1][j - 1] else 0
            }
        }
        return ways[s.length][t.length]
    }
}
