class Solution {
    fun checkInclusion(pattern: String, text: String): Boolean {
        val width = pattern.length
        if (width > text.length) return false
        val need = IntArray(26)
        val window = IntArray(26)
        for (ch in pattern) need[ch - 'a']++
        for (right in text.indices) {
            window[text[right] - 'a']++
            if (right >= width) window[text[right - width] - 'a']--
            if (right >= width - 1 && window.contentEquals(need)) return true
        }
        return false
    }
}
