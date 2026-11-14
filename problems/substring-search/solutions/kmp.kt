class Solution {
    fun findAllOccurrences(text: String, pattern: String): IntArray {
        val border = borderTable(pattern)
        val found = ArrayList<Int>()
        var matched = 0
        for (position in text.indices) {
            val letter = text[position]
            while (matched > 0 && letter != pattern[matched]) matched = border[matched - 1]
            if (letter == pattern[matched]) matched++
            if (matched == pattern.length) {
                found.add(position - pattern.length + 1)
                matched = border[matched - 1]
            }
        }
        return found.toIntArray()
    }

    // border[i] is the length of the longest proper prefix of pattern[0..i] that is also a suffix of it.
    private fun borderTable(pattern: String): IntArray {
        val border = IntArray(pattern.length)
        var length = 0
        for (i in 1 until pattern.length) {
            while (length > 0 && pattern[i] != pattern[length]) length = border[length - 1]
            if (pattern[i] == pattern[length]) length++
            border[i] = length
        }
        return border
    }
}
