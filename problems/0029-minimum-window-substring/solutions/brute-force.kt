class Solution {
    fun minWindow(s: String, t: String): String {
        val need = IntArray(128)
        for (ch in t) need[ch.code]++
        var bestStart = 0
        var bestLength = 0
        for (start in s.indices) {
            val remaining = need.copyOf()
            var missing = t.length
            for (end in start until s.length) {
                if (remaining[s[end].code]-- > 0) missing--
                if (missing == 0) {
                    if (bestLength == 0 || end - start + 1 < bestLength) {
                        bestStart = start
                        bestLength = end - start + 1
                    }
                    break
                }
            }
        }
        return s.substring(bestStart, bestStart + bestLength)
    }
}
