class Solution {
    fun isMatch(s: String, p: String): Boolean {
        fun fits(letter: Char, item: Char) = item == '.' || item == letter

        // previous[j]: s[:i - 1] matches p[:j]; current[j]: s[:i] matches p[:j].
        var previous = BooleanArray(p.length + 1)
        var current = BooleanArray(p.length + 1)
        for (i in 0..s.length) {
            current[0] = i == 0
            for (j in 1..p.length) {
                current[j] = if (p[j - 1] == '*') {
                    // "x*" matches nothing, or it matches s[i - 1] and possibly more before it.
                    current[j - 2] || (i > 0 && fits(s[i - 1], p[j - 2]) && previous[j])
                } else {
                    i > 0 && fits(s[i - 1], p[j - 1]) && previous[j - 1]
                }
            }
            previous = current.also { current = previous }
        }
        return previous[p.length]
    }
}
