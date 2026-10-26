class Solution {
    fun characterReplacement(s: String, k: Int): Int {
        var best = 0
        for (start in s.indices) {
            val counts = IntArray(26)
            var most = 0
            for (end in start until s.length) {
                most = maxOf(most, ++counts[s[end] - 'A'])
                if (end - start + 1 - most > k) break
                best = maxOf(best, end - start + 1)
            }
        }
        return best
    }
}
