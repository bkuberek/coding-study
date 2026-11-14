class Solution {
    fun partition(s: String): List<List<String>> {
        val result = mutableListOf<List<String>>()
        val pieces = ArrayList<String>()

        fun isPalindrome(from: Int, to: Int): Boolean {
            var left = from
            var right = to
            while (left < right) {
                if (s[left++] != s[right--]) return false
            }
            return true
        }

        fun cutFrom(start: Int) {
            if (start == s.length) {
                result.add(pieces.toList())
                return
            }
            for (end in start until s.length) {
                if (isPalindrome(start, end)) {
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
