class Solution {
    fun setZeroes(matrix: Array<IntArray>) {
        // Find every row and column to clear before clearing anything.
        val zeroRows = HashSet<Int>()
        val zeroCols = HashSet<Int>()
        for ((r, row) in matrix.withIndex()) {
            for ((c, value) in row.withIndex()) {
                if (value == 0) {
                    zeroRows.add(r)
                    zeroCols.add(c)
                }
            }
        }
        for ((r, row) in matrix.withIndex()) {
            for (c in row.indices) {
                if (r in zeroRows || c in zeroCols) row[c] = 0
            }
        }
    }
}
