class Solution {
    fun solveNQueens(n: Int): List<List<String>> {
        val boards = mutableListOf<List<String>>()
        val queenColumn = IntArray(n)
        val columns = BooleanArray(n)
        // Squares on one diagonal share row - col (shifted by n - 1 to index from 0); on one
        // anti-diagonal they share row + col.
        val diagonals = BooleanArray(2 * n - 1)
        val antiDiagonals = BooleanArray(2 * n - 1)

        fun mark(row: Int, col: Int, used: Boolean) {
            columns[col] = used
            diagonals[row - col + n - 1] = used
            antiDiagonals[row + col] = used
        }

        fun place(row: Int) {
            if (row == n) {
                boards.add(queenColumn.map { col -> ".".repeat(col) + "Q" + ".".repeat(n - col - 1) })
                return
            }
            for (col in 0 until n) {
                if (columns[col] || diagonals[row - col + n - 1] || antiDiagonals[row + col]) continue
                mark(row, col, true)
                queenColumn[row] = col
                place(row + 1)
                mark(row, col, false)
            }
        }

        place(0)
        return boards
    }
}
