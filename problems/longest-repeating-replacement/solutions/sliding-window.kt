class Solution {
    fun characterReplacement(s: String, k: Int): Int {
        val counts = IntArray(26)
        var most = 0
        var left = 0
        var best = 0
        for (right in s.indices) {
            most = maxOf(most, ++counts[s[right] - 'A'])
            if (right - left + 1 - most > k) {
                counts[s[left] - 'A']--
                left++
            }
            best = maxOf(best, right - left + 1)
        }
        return best
    }
}
