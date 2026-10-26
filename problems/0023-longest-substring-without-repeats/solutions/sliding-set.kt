class Solution {
    fun lengthOfLongestSubstring(s: String): Int {
        val window = HashSet<Char>()
        var left = 0
        var best = 0
        for (ch in s) {
            while (ch in window) {
                window.remove(s[left])
                left++
            }
            window.add(ch)
            best = maxOf(best, window.size)
        }
        return best
    }
}
