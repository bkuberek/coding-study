class Solution {
    fun longestPalindrome(s: String): String {
        val n = s.length
        // isPalindrome[i][j] tells whether s[i..j] (inclusive) is a palindrome.
        val isPalindrome = Array(n) { BooleanArray(n) }
        var bestStart = 0
        var bestLength = 1
        for (i in 0 until n) isPalindrome[i][i] = true
        for (length in 2..n) {
            for (i in 0..n - length) {
                val j = i + length - 1
                if (s[i] == s[j] && (length == 2 || isPalindrome[i + 1][j - 1])) {
                    isPalindrome[i][j] = true
                    bestStart = i
                    bestLength = length
                }
            }
        }
        return s.substring(bestStart, bestStart + bestLength)
    }
}
