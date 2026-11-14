class Solution {
    fun isInterleave(s1: String, s2: String, s3: String): Boolean {
        if (s1.length + s2.length != s3.length) return false
        // reach[i][j]: s1[:i] and s2[:j] interleave to s3[:i + j].
        val reach = Array(s1.length + 1) { BooleanArray(s2.length + 1) }
        reach[0][0] = true
        for (i in 0..s1.length) {
            for (j in 0..s2.length) {
                // The last character of s3[:i + j] came from s1 or from s2.
                val fromFirst = i > 0 && reach[i - 1][j] && s1[i - 1] == s3[i + j - 1]
                val fromSecond = j > 0 && reach[i][j - 1] && s2[j - 1] == s3[i + j - 1]
                if (fromFirst || fromSecond) reach[i][j] = true
            }
        }
        return reach[s1.length][s2.length]
    }
}
