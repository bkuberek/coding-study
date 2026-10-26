class Solution {
    fun wordBreak(s: String, wordDict: Array<String>): Boolean {
        val words = wordDict.toHashSet()
        val longest = wordDict.maxOf { it.length }
        // ok[i] is true when the prefix s[0 until i] can be split into dictionary words.
        val ok = BooleanArray(s.length + 1)
        ok[0] = true
        for (end in 1..s.length) {
            ok[end] = (maxOf(0, end - longest) until end).any { start ->
                ok[start] && s.substring(start, end) in words
            }
        }
        return ok[s.length]
    }
}
