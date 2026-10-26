class Solution {
    fun numDecodings(s: String): Int {
        // memo[start] is the number of readings of the suffix s[start..], or -1 when unknown.
        val memo = IntArray(s.length) { -1 }

        fun waysFrom(start: Int): Int {
            if (start == s.length) return 1
            if (s[start] == '0') return 0
            if (memo[start] == -1) {
                var count = waysFrom(start + 1)
                if (start + 1 < s.length && s.substring(start, start + 2).toInt() <= 26) {
                    count += waysFrom(start + 2)
                }
                memo[start] = count
            }
            return memo[start]
        }

        return waysFrom(0)
    }
}
