class Solution {
    fun searchMatrix(matrix: Array<IntArray>, target: Int): Boolean {
        // Everything left of the current cell in its row is smaller or equal; everything
        // below it in its column is larger or equal.
        var row = 0
        var column = matrix[0].lastIndex
        while (row < matrix.size && column >= 0) {
            val value = matrix[row][column]
            when {
                value == target -> return true
                value > target -> column--
                else -> row++
            }
        }
        return false
    }
}
