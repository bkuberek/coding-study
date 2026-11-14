class Solution {
    fun isInterleave(s1: String, s2: String, s3: String): Boolean {
        if (s1.length + s2.length != s3.length) return false
        // known[i][j] caches whether s1[i:] and s2[j:] interleave to s3[i + j:]; null is unknown.
        val known = Array(s1.length + 1) { arrayOfNulls<Boolean>(s2.length + 1) }

        fun solve(i: Int, j: Int): Boolean {
            if (i == s1.length && j == s2.length) return true
            return known[i][j] ?: run {
                val next = s3[i + j]
                // The next character of s3 comes from s1 or from s2.
                val fits = (i < s1.length && s1[i] == next && solve(i + 1, j)) ||
                    (j < s2.length && s2[j] == next && solve(i, j + 1))
                known[i][j] = fits
                fits
            }
        }

        return solve(0, 0)
    }
}
