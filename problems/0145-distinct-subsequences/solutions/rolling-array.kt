class Solution {
    fun numDistinct(s: String, t: String): Int {
        // ways[j] counts the occurrences of t[:j] in the prefix of s read so far.
        val ways = IntArray(t.length + 1)
        ways[0] = 1
        for (character in s) {
            // Right to left: ways[j - 1] still excludes this character, so it is used once.
            for (j in t.length downTo 1) {
                if (t[j - 1] == character) {
                    ways[j] += ways[j - 1]
                }
            }
        }
        return ways[t.length]
    }
}
