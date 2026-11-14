private const val SAFE = 'S'

class Solution {
    fun solve(board: Array<CharArray>) {
        val rows = board.size
        val cols = board[0].size
        // Every 'O' on the edge is safe; so is everything connected to one of them.
        val stack = ArrayDeque<Int>()
        for (r in 0 until rows) {
            for (c in 0 until cols) {
                val onEdge = r == 0 || r == rows - 1 || c == 0 || c == cols - 1
                if (onEdge && board[r][c] == 'O') {
                    board[r][c] = SAFE
                    stack.addLast(r * cols + c)
                }
            }
        }
        while (stack.isNotEmpty()) {
            val cell = stack.removeLast()
            val r = cell / cols
            val c = cell % cols
            for ((nr, nc) in listOf(r + 1 to c, r - 1 to c, r to c + 1, r to c - 1)) {
                if (nr in 0 until rows && nc in 0 until cols && board[nr][nc] == 'O') {
                    board[nr][nc] = SAFE
                    stack.addLast(nr * cols + nc)
                }
            }
        }
        for (row in board) {
            for (c in row.indices) {
                row[c] = if (row[c] == SAFE) 'O' else 'X'
            }
        }
    }
}
