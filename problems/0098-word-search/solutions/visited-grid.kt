private val STEPS = arrayOf(intArrayOf(1, 0), intArrayOf(-1, 0), intArrayOf(0, 1), intArrayOf(0, -1))

class Solution {
    fun exist(board: Array<CharArray>, word: String): Boolean {
        val rows = board.size
        val cols = board[0].size
        val visited = Array(rows) { BooleanArray(cols) }

        // Whether word[k..] can be spelled by a walk that starts at (r, c).
        fun spellsFrom(r: Int, c: Int, k: Int): Boolean {
            if (r !in 0 until rows || c !in 0 until cols || visited[r][c] || board[r][c] != word[k]) {
                return false
            }
            if (k == word.length - 1) return true
            visited[r][c] = true
            val found = STEPS.any { (dr, dc) -> spellsFrom(r + dr, c + dc, k + 1) }
            visited[r][c] = false
            return found
        }

        return (0 until rows).any { r -> (0 until cols).any { c -> spellsFrom(r, c, 0) } }
    }
}
