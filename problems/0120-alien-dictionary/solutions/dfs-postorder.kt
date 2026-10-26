private const val LETTERS = 26
private const val UNVISITED = 0
private const val ON_PATH = 1
private const val DONE = 2

class Solution {
    fun alienOrder(words: Array<String>): String {
        val present = BooleanArray(LETTERS)
        for (word in words) for (letter in word) present[letter - 'a'] = true
        // before[x][y]: letter x must come before letter y.
        val before = Array(LETTERS) { BooleanArray(LETTERS) }
        for ((first, second) in words.asList().zipWithNext()) {
            val k = first.zip(second).indexOfFirst { (a, b) -> a != b }
            if (k >= 0) {
                before[first[k] - 'a'][second[k] - 'a'] = true
            } else if (first.length > second.length) {
                return "" // a word placed before its own proper prefix
            }
        }
        val state = IntArray(LETTERS) { UNVISITED }
        val finished = StringBuilder() // each letter lands here after every letter that must follow it

        // Emit everything after x, then x; false if a rule loops back.
        fun visit(x: Int): Boolean {
            state[x] = ON_PATH
            for (y in 0 until LETTERS) {
                if (!before[x][y]) continue
                if (state[y] == ON_PATH || (state[y] == UNVISITED && !visit(y))) return false
            }
            state[x] = DONE
            finished.append('a' + x)
            return true
        }

        for (x in 0 until LETTERS) {
            if (present[x] && state[x] == UNVISITED && !visit(x)) return ""
        }
        return finished.reverse().toString()
    }
}
