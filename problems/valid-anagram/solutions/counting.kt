private const val ALPHABET_SIZE = 26

class Solution {
    fun isAnagram(s: String, t: String): Boolean {
        if (s.length != t.length) {
            return false
        }
        val counts = IntArray(ALPHABET_SIZE)
        for (letter in s) {
            counts[letter - 'a']++
        }
        for (letter in t) {
            if (--counts[letter - 'a'] < 0) {
                return false
            }
        }
        return true
    }
}
