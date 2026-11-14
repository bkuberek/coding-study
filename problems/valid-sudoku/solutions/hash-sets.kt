private const val SIDE = 9
private const val BOX = 3
private const val EMPTY = '.'

class Solution {
    fun isValidSudoku(board: Array<CharArray>): Boolean {
        val rows = List(SIDE) { HashSet<Char>() }
        val columns = List(SIDE) { HashSet<Char>() }
        val boxes = List(SIDE) { HashSet<Char>() }
        for (row in 0 until SIDE) {
            for (column in 0 until SIDE) {
                val digit = board[row][column]
                if (digit == EMPTY) {
                    continue
                }
                val box = (row / BOX) * BOX + column / BOX
                // add returns false when the digit is already present.
                if (!rows[row].add(digit) || !columns[column].add(digit) || !boxes[box].add(digit)) {
                    return false
                }
            }
        }
        return true
    }
}
