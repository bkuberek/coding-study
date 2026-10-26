class Solution {
    fun numDistinct(s: String, t: String): Int {
        // ways[i][j] caches the occurrences of t[j:] as a subsequence of s[i:]; -1 is unknown.
        val ways = Array(s.length) { IntArray(t.length) { -1 } }

        fun count(i: Int, j: Int): Int {
            if (j == t.length) return 1 // the empty suffix of t occurs once
            if (s.length - i < t.length - j) return 0 // not enough characters left in s
            if (ways[i][j] < 0) {
                // Either s[i] is skipped, or it is matched with t[j].
                ways[i][j] = count(i + 1, j) + if (s[i] == t[j]) count(i + 1, j + 1) else 0
            }
            return ways[i][j]
        }

        return count(0, 0)
    }
}
