class Solution {
    fun partition(s: String): List<List<String>> {
        val n = s.length
        // palindrome[i][j]: whether s[i..j] reads the same both ways. Row i depends on row i + 1.
        val palindrome = Array(n) { BooleanArray(n) }
        for (i in n - 1 downTo 0) {
            for (j in i until n) {
                palindrome[i][j] = s[i] == s[j] && (j - i < 2 || palindrome[i + 1][j - 1])
            }
        }
        val result = mutableListOf<List<String>>()
        val pieces = ArrayList<String>()

        fun cutFrom(start: Int) {
            if (start == n) {
                result.add(pieces.toList())
                return
            }
            for (end in start until n) {
                if (palindrome[start][end]) {
                    pieces.add(s.substring(start, end + 1))
                    cutFrom(end + 1)
                    pieces.removeAt(pieces.size - 1)
                }
            }
        }

        cutFrom(0)
        return result
    }
}
