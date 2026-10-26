class Solution {
    fun lengthOfLongestSubstring(s: String): Int {
        var best = 0
        for (start in s.indices) {
            val seen = BooleanArray(128)
            var end = start
            while (end < s.length && !seen[s[end].code]) {
                seen[s[end].code] = true
                end++
            }
            best = maxOf(best, end - start)
        }
        return best
    }
}
