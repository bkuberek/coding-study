class Solution {
    fun findAllOccurrences(text: String, pattern: String): IntArray {
        val windowSize = pattern.length
        if (windowSize > text.length) return IntArray(0)
        var leavingWeight = 1L
        repeat(windowSize - 1) { leavingWeight = leavingWeight * BASE % MODULUS }
        var target = 0L
        var window = 0L
        for (i in 0 until windowSize) {
            target = (target * BASE + pattern[i].code) % MODULUS
            window = (window * BASE + text[i].code) % MODULUS
        }
        val found = ArrayList<Int>()
        for (start in 0..text.length - windowSize) {
            if (window == target && text.startsWith(pattern, start)) found.add(start)
            if (start + windowSize < text.length) {
                val without = (window - text[start].code * leavingWeight % MODULUS + MODULUS) % MODULUS
                window = (without * BASE + text[start + windowSize].code) % MODULUS
            }
        }
        return found.toIntArray()
    }

    private companion object {
        const val BASE = 131L
        const val MODULUS = 1_000_000_007L
    }
}
