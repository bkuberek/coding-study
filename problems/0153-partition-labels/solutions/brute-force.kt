class Solution {
    fun partitionLabels(s: String): IntArray {
        val sizes = mutableListOf<Int>()
        var start = 0
        while (start < s.length) {
            // The piece must reach the last copy of every letter it contains.
            var end = s.lastIndexOf(s[start])
            var position = start
            while (position <= end) {
                end = maxOf(end, s.lastIndexOf(s[position]))
                position++
            }
            sizes.add(end - start + 1)
            start = end + 1
        }
        return sizes.toIntArray()
    }
}
