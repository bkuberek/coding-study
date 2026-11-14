class Solution {
    fun lengthOfLongestSubstring(s: String): Int {
        val lastSeen = IntArray(128) { -1 }
        var left = 0
        var best = 0
        for ((right, ch) in s.withIndex()) {
            if (lastSeen[ch.code] >= left) {
                left = lastSeen[ch.code] + 1
            }
            lastSeen[ch.code] = right
            best = maxOf(best, right - left + 1)
        }
        return best
    }
}
