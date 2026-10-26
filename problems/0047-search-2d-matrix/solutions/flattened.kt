class Solution {
    fun searchMatrix(matrix: Array<IntArray>, target: Int): Boolean {
        val columns = matrix[0].size
        var low = 0
        var high = matrix.size * columns - 1
        while (low <= high) {
            val middle = (low + high) ushr 1
            val value = matrix[middle / columns][middle % columns]
            when {
                value == target -> return true
                value < target -> low = middle + 1
                else -> high = middle - 1
            }
        }
        return false
    }
}
