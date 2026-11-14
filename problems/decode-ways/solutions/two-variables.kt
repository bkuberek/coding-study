class Solution {
    fun numDecodings(s: String): Int {
        // Before digit i: oneBack counts readings of s[0 until i], twoBack those of s[0 until i - 1].
        var twoBack = 0
        var oneBack = 1
        for (i in s.indices) {
            var current = if (s[i] != '0') oneBack else 0
            if (i > 0 && (s[i - 1].digitToInt() * 10 + s[i].digitToInt()) in 10..26) {
                current += twoBack
            }
            twoBack = oneBack
            oneBack = current
        }
        return oneBack
    }
}
