class Solution {
    fun partitionLabels(s: String): IntArray {
        val last = IntArray(26)
        s.forEachIndexed { index, letter -> last[letter - 'a'] = index }
        val sizes = mutableListOf<Int>()
        var start = 0
        var end = 0
        for ((index, letter) in s.withIndex()) {
            end = maxOf(end, last[letter - 'a'])
            if (index == end) {
                // Every letter seen since `start` has no copy after this point: cut here.
                sizes.add(end - start + 1)
                start = index + 1
            }
        }
        return sizes.toIntArray()
    }
}
