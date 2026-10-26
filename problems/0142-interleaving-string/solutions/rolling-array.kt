class Solution {
    fun isInterleave(s1: String, s2: String, s3: String): Boolean {
        if (s1.length + s2.length != s3.length) return false
        // Swapping the sources does not change the answer, so let the row run along the shorter.
        val (longer, shorter) = if (s1.length >= s2.length) s1 to s2 else s2 to s1
        // Before row i is processed, reach[j] tells whether longer[:i - 1] and shorter[:j]
        // interleave to s3[:i - 1 + j]; afterwards it holds row i.
        val reach = BooleanArray(shorter.length + 1)
        for (i in 0..longer.length) {
            for (j in 0..shorter.length) {
                if (i == 0 && j == 0) {
                    reach[j] = true
                    continue
                }
                val fromLonger = i > 0 && reach[j] && longer[i - 1] == s3[i + j - 1]
                val fromShorter = j > 0 && reach[j - 1] && shorter[j - 1] == s3[i + j - 1]
                reach[j] = fromLonger || fromShorter
            }
        }
        return reach[shorter.length]
    }
}
