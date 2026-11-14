private val STEPS = arrayOf(intArrayOf(1, 0), intArrayOf(-1, 0), intArrayOf(0, 1), intArrayOf(0, -1))
private const val USED = '#'

class Solution {
    fun exist(board: Array<CharArray>, word: String): Boolean {
        val rows = board.size
        val cols = board[0].size
        val available = board.flatMap { it.asIterable() }.groupingBy { it }.eachCount()
        val needed = word.groupingBy { it }.eachCount()
        if (needed.any { (letter, count) -> available.getOrDefault(letter, 0) < count }) return false
        // A walk read backwards is also a walk: start from whichever end is rarer on the board.
        val target = if (available.getValue(word.first()) > available.getValue(word.last())) word.reversed() else word

        fun spellsFrom(r: Int, c: Int, k: Int): Boolean {
            if (board[r][c] != target[k]) return false
            if (k == target.length - 1) return true
            board[r][c] = USED
            val found = STEPS.any { (dr, dc) ->
                val nr = r + dr
                val nc = c + dc
                nr in 0 until rows && nc in 0 until cols && spellsFrom(nr, nc, k + 1)
            }
            board[r][c] = target[k]
            return found
        }

        return (0 until rows).any { r -> (0 until cols).any { c -> spellsFrom(r, c, 0) } }
    }
}
