class Solution {
    fun searchMatrix(matrix: Array<IntArray>, target: Int): Boolean =
        matrix.any { row -> row.any { it == target } }
}
