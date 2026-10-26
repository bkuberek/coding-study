private const val SIDE = 9
private const val BOX = 3
private const val EMPTY = '.'

class Solution {
    fun isValidSudoku(board: Array<CharArray>): Boolean {
        // Bit d - 1 of a mask is set once digit d has been seen in that row, column or box.
        val rows = IntArray(SIDE)
        val columns = IntArray(SIDE)
        val boxes = IntArray(SIDE)
        for (row in 0 until SIDE) {
            for (column in 0 until SIDE) {
                val cell = board[row][column]
                if (cell == EMPTY) {
                    continue
                }
                val bit = 1 shl (cell - '1')
                val box = (row / BOX) * BOX + column / BOX
                if (((rows[row] or columns[column] or boxes[box]) and bit) != 0) {
                    return false
                }
                rows[row] = rows[row] or bit
                columns[column] = columns[column] or bit
                boxes[box] = boxes[box] or bit
            }
        }
        return true
    }
}
