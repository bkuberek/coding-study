class Solution {
    fun longestPalindrome(s: String): String {
        // Interleave a separator so every palindrome has odd length: "ab" becomes "|a|b|".
        val t = CharArray(2 * s.length + 1) { if (it % 2 == 1) s[it / 2] else '|' }
        // radius[i] is how far the palindrome centered at t[i] extends to each side.
        val radius = IntArray(t.size)
        var center = 0
        var right = 0 // the palindrome reaching furthest right is t[2 * center - right .. right]
        var best = 0
        for (i in t.indices) {
            if (i < right) {
                // Mirror of i around center; its radius is valid up to the right boundary.
                radius[i] = minOf(right - i, radius[2 * center - i])
            }
            while (i - radius[i] - 1 >= 0 &&
                i + radius[i] + 1 < t.size &&
                t[i - radius[i] - 1] == t[i + radius[i] + 1]
            ) {
                radius[i]++
            }
            if (i + radius[i] > right) {
                center = i
                right = i + radius[i]
            }
            if (radius[i] > radius[best]) best = i
        }
        // A radius r around position i of t covers r characters of s starting at (i - r) / 2.
        val start = (best - radius[best]) / 2
        return s.substring(start, start + radius[best])
    }
}
