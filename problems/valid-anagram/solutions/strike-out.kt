class Solution {
    fun isAnagram(s: String, t: String): Boolean {
        if (s.length != t.length) {
            return false
        }
        val used = BooleanArray(t.length)
        for (letter in s) {
            var position = 0
            while (position < t.length && (used[position] || t[position] != letter)) {
                position++
            }
            if (position == t.length) {
                return false
            }
            used[position] = true
        }
        return true
    }
}
