class Solution {
    fun longestPalindrome(s: String): String {
        var bestStart = 0
        var bestLength = 1
        // Center c sits on character c / 2 when c is even, between two characters when c is odd.
        for (center in 0 until 2 * s.length - 1) {
            var left = center / 2
            var right = (center + 1) / 2
            while (left >= 0 && right < s.length && s[left] == s[right]) {
                left--
                right++
            }
            // The loop overshoots by one on each side: the palindrome is s[left + 1 .. right - 1].
            if (right - left - 1 > bestLength) {
                bestStart = left + 1
                bestLength = right - left - 1
            }
        }
        return s.substring(bestStart, bestStart + bestLength)
    }
}
