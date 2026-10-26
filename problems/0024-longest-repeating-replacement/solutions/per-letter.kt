class Solution {
    fun characterReplacement(s: String, k: Int): Int {
        var best = 0
        for (target in s.toSet()) {
            var left = 0
            var others = 0
            for (right in s.indices) {
                if (s[right] != target) others++
                while (others > k) {
                    if (s[left] != target) others--
                    left++
                }
                best = maxOf(best, right - left + 1)
            }
        }
        return best
    }
}
