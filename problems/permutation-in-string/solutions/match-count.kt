class Solution {
    fun checkInclusion(pattern: String, text: String): Boolean {
        val width = pattern.length
        if (width > text.length) return false
        val surplus = IntArray(26)
        for (ch in pattern) surplus[ch - 'a']--
        var balanced = surplus.count { it == 0 }

        fun shift(letter: Int, delta: Int) {
            if (surplus[letter] == 0) balanced--
            surplus[letter] += delta
            if (surplus[letter] == 0) balanced++
        }

        for (right in text.indices) {
            shift(text[right] - 'a', 1)
            if (right >= width) shift(text[right - width] - 'a', -1)
            if (balanced == 26) return true
        }
        return false
    }
}
