class Solution {
    fun isPalindrome(s: String): Boolean {
        val cleaned = s.filter { it.isLetterOrDigit() }.lowercase()
        return cleaned == cleaned.reversed()
    }
}
