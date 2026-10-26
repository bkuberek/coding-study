class Solution {
    fun wordBreak(s: String, wordDict: Array<String>): Boolean {
        // memo[start] answers "can the suffix s[start..] be split?"; null means not computed.
        val memo = arrayOfNulls<Boolean>(s.length)

        fun canSplitFrom(start: Int): Boolean {
            if (start == s.length) return true
            memo[start]?.let { return it }
            val result = wordDict.any { word ->
                s.startsWith(word, start) && canSplitFrom(start + word.length)
            }
            memo[start] = result
            return result
        }

        return canSplitFrom(0)
    }
}
