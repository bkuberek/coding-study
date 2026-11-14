class Solution {
    fun spiralOrder(matrix: Array<IntArray>): IntArray {
        var top = 0
        var bottom = matrix.size - 1
        var left = 0
        var right = matrix[0].size - 1
        val order = ArrayList<Int>(matrix.size * matrix[0].size)
        while (top <= bottom && left <= right) {
            for (c in left..right) order.add(matrix[top][c])
            for (r in top + 1..bottom) order.add(matrix[r][right])
            // Only a ring with two rows and two columns has a bottom row and left column of its own.
            if (top < bottom && left < right) {
                for (c in right - 1 downTo left) order.add(matrix[bottom][c])
                for (r in bottom - 1 downTo top + 1) order.add(matrix[r][left])
            }
            top++
            bottom--
            left++
            right--
        }
        return order.toIntArray()
    }
}
