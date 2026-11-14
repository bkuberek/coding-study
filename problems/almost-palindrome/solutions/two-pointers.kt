class Solution {
    fun validPalindrome(s: String): Boolean {
        var left = 0
        var right = s.length - 1
        while (left < right) {
            if (s[left] != s[right]) {
                return isPalindrome(s, left + 1, right) || isPalindrome(s, left, right - 1)
            }
            left++
            right--
        }
        return true
    }

    private fun isPalindrome(s: String, from: Int, to: Int): Boolean {
        var left = from
        var right = to
        while (left < right) {
            if (s[left++] != s[right--]) {
                return false
            }
        }
        return true
    }
}
