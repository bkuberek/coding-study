private const val SIDE = 9
private const val BOX = 3
private const val EMPTY = '.'

class Solution {
    fun isValidSudoku(board: Array<CharArray>): Boolean {
        for (row in 0 until SIDE) {
            for (column in 0 until SIDE) {
                val digit = board[row][column]
                if (digit != EMPTY && repeats(board, row, column, digit)) {
                    return false
                }
            }
        }
        return true
    }

    // Whether another cell in the same row, column or box holds `digit`.
    private fun repeats(board: Array<CharArray>, row: Int, column: Int, digit: Char): Boolean {
        val top = row - row % BOX
        val left = column - column % BOX
        for (i in 0 until SIDE) {
            if (i != column && board[row][i] == digit) {
                return true
            }
            if (i != row && board[i][column] == digit) {
                return true
            }
            val boxRow = top + i / BOX
            val boxColumn = left + i % BOX
            if ((boxRow != row || boxColumn != column) && board[boxRow][boxColumn] == digit) {
                return true
            }
        }
        return false
    }
}
