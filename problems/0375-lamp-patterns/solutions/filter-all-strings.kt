class Solution {
    fun lampPatterns(n: Int): List<String> {
        val result = mutableListOf<String>()
        for (number in 0 until (1 shl n)) {
            // Counting up writes the strings in increasing order; the bits are the lamps.
            val pattern = number.toString(2).padStart(n, '0')
            if ("11" !in pattern) {
                result.add(pattern)
            }
        }
        return result
    }
}
