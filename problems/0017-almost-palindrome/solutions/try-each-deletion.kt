class Solution {
    fun validPalindrome(s: String): Boolean {
        if (isPalindrome(s)) {
            return true
        }
        return s.indices.any { index -> isPalindrome(s.removeRange(index, index + 1)) }
    }

    private fun isPalindrome(text: String): Boolean {
        var left = 0
        var right = text.length - 1
        while (left < right) {
            if (text[left++] != text[right--]) {
                return false
            }
        }
        return true
    }
}
