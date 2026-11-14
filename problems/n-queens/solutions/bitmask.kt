class Solution {
    fun solveNQueens(n: Int): List<List<String>> {
        val full = (1 shl n) - 1
        val boards = mutableListOf<List<String>>()
        val queenColumn = IntArray(n)

        // Each mask marks the squares of the current row attacked along one kind of line.
        fun place(row: Int, columns: Int, diagonals: Int, antiDiagonals: Int) {
            if (columns == full) {
                boards.add(queenColumn.map { col -> ".".repeat(col) + "Q" + ".".repeat(n - col - 1) })
                return
            }
            var free = full and (columns or diagonals or antiDiagonals).inv()
            while (free != 0) {
                val bit = free and -free // lowest free square
                free = free xor bit
                queenColumn[row] = Integer.numberOfTrailingZeros(bit)
                // Moving one row down shifts each diagonal attack one column over.
                place(row + 1, columns or bit, ((diagonals or bit) shl 1) and full, (antiDiagonals or bit) shr 1)
            }
        }

        place(0, 0, 0, 0)
        return boards
    }
}
