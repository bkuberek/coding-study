class Solution {
    fun longestCommonSubsequence(text1: String, text2: String): Int {
        // The answer is symmetric, so let the rows run along the shorter string.
        val (longer, shorter) = if (text1.length >= text2.length) text1 to text2 else text2 to text1
        // previous[j] is the answer for the prefixes longer[:i - 1] and shorter[:j].
        var previous = IntArray(shorter.length + 1)
        var current = IntArray(shorter.length + 1)
        for (character in longer) {
            for (j in 1..shorter.length) {
                current[j] = if (character == shorter[j - 1]) {
                    previous[j - 1] + 1
                } else {
                    maxOf(previous[j], current[j - 1])
                }
            }
            previous = current.also { current = previous }
        }
        return previous[shorter.length]
    }
}
