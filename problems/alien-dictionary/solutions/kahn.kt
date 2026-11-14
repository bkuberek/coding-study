private const val LETTERS = 26

class Solution {
    fun alienOrder(words: Array<String>): String {
        val present = BooleanArray(LETTERS)
        for (word in words) for (letter in word) present[letter - 'a'] = true
        // before[x][y]: letter x must come before letter y. A matrix dedupes repeated rules.
        val before = Array(LETTERS) { BooleanArray(LETTERS) }
        for ((first, second) in words.asList().zipWithNext()) {
            val k = first.zip(second).indexOfFirst { (a, b) -> a != b }
            if (k >= 0) {
                before[first[k] - 'a'][second[k] - 'a'] = true
            } else if (first.length > second.length) {
                return "" // a word placed before its own proper prefix
            }
        }
        val waiting = IntArray(LETTERS) { y -> (0 until LETTERS).count { x -> before[x][y] } }
        val ready = ArrayDeque((0 until LETTERS).filter { present[it] && waiting[it] == 0 })
        val order = StringBuilder()
        while (ready.isNotEmpty()) {
            val x = ready.removeFirst()
            order.append('a' + x)
            for (y in 0 until LETTERS) {
                if (before[x][y] && --waiting[y] == 0) ready.addLast(y)
            }
        }
        return if (order.length == present.count { it }) order.toString() else ""
    }
}
