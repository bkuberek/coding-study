class Solution {
    fun minWindow(s: String, t: String): String {
        val deficit = IntArray(128)
        for (ch in t) deficit[ch.code]++
        val useful = s.indices.filter { deficit[s[it].code] > 0 }
        var missing = t.length
        var bestStart = 0
        var bestLength = 0
        var left = 0
        for (right in useful) {
            if (deficit[s[right].code]-- > 0) missing--
            while (missing == 0) {
                val start = useful[left]
                if (bestLength == 0 || right - start + 1 < bestLength) {
                    bestStart = start
                    bestLength = right - start + 1
                }
                if (++deficit[s[start].code] > 0) missing++
                left++
            }
        }
        return s.substring(bestStart, bestStart + bestLength)
    }
}
