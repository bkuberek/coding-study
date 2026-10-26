class Solution {
    fun isMatch(s: String, p: String): Boolean {
        fun fits(letter: Char, item: Char) = item == '.' || item == letter

        // matches[i][j]: s[:i] matches p[:j].
        val matches = Array(s.length + 1) { BooleanArray(p.length + 1) }
        matches[0][0] = true
        for (i in 0..s.length) {
            for (j in 1..p.length) {
                matches[i][j] = if (p[j - 1] == '*') {
                    // "x*" matches nothing, or it matches s[i - 1] and possibly more before it.
                    matches[i][j - 2] || (i > 0 && fits(s[i - 1], p[j - 2]) && matches[i - 1][j])
                } else {
                    i > 0 && fits(s[i - 1], p[j - 1]) && matches[i - 1][j - 1]
                }
            }
        }
        return matches[s.length][p.length]
    }
}
