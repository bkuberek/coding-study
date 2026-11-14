class Solution {
    fun findAllOccurrences(text: String, pattern: String): IntArray {
        val found = ArrayList<Int>()
        for (start in 0..text.length - pattern.length) {
            var offset = 0
            while (offset < pattern.length && text[start + offset] == pattern[offset]) offset++
            if (offset == pattern.length) found.add(start)
        }
        return found.toIntArray()
    }
}
