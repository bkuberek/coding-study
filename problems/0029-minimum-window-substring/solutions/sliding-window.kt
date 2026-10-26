class Solution {
    fun minWindow(s: String, t: String): String {
        val deficit = IntArray(128)
        for (ch in t) deficit[ch.code]++
        var missing = t.length
        var bestStart = 0
        var bestLength = 0
        var left = 0
        for (right in s.indices) {
            if (deficit[s[right].code]-- > 0) missing--
            while (missing == 0) {
                if (bestLength == 0 || right - left + 1 < bestLength) {
                    bestStart = left
                    bestLength = right - left + 1
                }
                if (++deficit[s[left].code] > 0) missing++
                left++
            }
        }
        return s.substring(bestStart, bestStart + bestLength)
    }
}
