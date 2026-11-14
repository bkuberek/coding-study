import kotlin.math.abs

class Solution {
    fun solveNQueens(n: Int): List<List<String>> {
        val boards = mutableListOf<List<String>>()
        // queenColumn[r] is the column of the queen in row r, for rows 0 until row.
        val queenColumn = IntArray(n)

        fun isSafe(row: Int, col: Int): Boolean =
            (0 until row).all { otherRow ->
                val otherCol = queenColumn[otherRow]
                col != otherCol && abs(col - otherCol) != row - otherRow
            }

        fun place(row: Int) {
            if (row == n) {
                boards.add(queenColumn.map { col -> ".".repeat(col) + "Q" + ".".repeat(n - col - 1) })
                return
            }
            for (col in 0 until n) {
                if (isSafe(row, col)) {
                    queenColumn[row] = col
                    place(row + 1)
                }
            }
        }

        place(0)
        return boards
    }
}
