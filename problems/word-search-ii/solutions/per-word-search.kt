class Solution {
    fun findWords(board: Array<CharArray>, words: Array<String>): List<String> =
        words.filter { word -> onBoard(board, word) }

    private fun onBoard(board: Array<CharArray>, word: String): Boolean =
        board.indices.any { row -> board[0].indices.any { col -> trace(board, word, row, col, 0) } }

    /** Can word[position..] be spelled starting at this cell? */
    private fun trace(board: Array<CharArray>, word: String, row: Int, col: Int, position: Int): Boolean {
        if (board[row][col] != word[position]) return false
        if (position == word.length - 1) return true
        board[row][col] = USED
        val found = STEPS.any { (dr, dc) ->
            val r = row + dr
            val c = col + dc
            r in board.indices && c in board[0].indices && trace(board, word, r, c, position + 1)
        }
        board[row][col] = word[position]
        return found
    }

    private companion object {
        const val USED = '#'
        val STEPS = listOf(1 to 0, -1 to 0, 0 to 1, 0 to -1)
    }
}
