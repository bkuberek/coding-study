class Solution {
    fun isMatch(s: String, p: String): Boolean {
        // known[i][j] caches whether s[i:] matches p[j:]; null is unknown.
        val known = Array(s.length + 1) { arrayOfNulls<Boolean>(p.length + 1) }

        fun solve(i: Int, j: Int): Boolean {
            if (j == p.length) return i == s.length
            return known[i][j] ?: run {
                val first = i < s.length && (p[j] == s[i] || p[j] == '.')
                val matched = if (j + 1 < p.length && p[j + 1] == '*') {
                    // Skip "x*" entirely, or let it eat one more character and stay on it.
                    solve(i, j + 2) || (first && solve(i + 1, j))
                } else {
                    first && solve(i + 1, j + 1)
                }
                known[i][j] = matched
                matched
            }
        }

        return solve(0, 0)
    }
}
