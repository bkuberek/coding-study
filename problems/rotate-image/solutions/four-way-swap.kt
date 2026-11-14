class Solution {
    fun rotate(matrix: Array<IntArray>) {
        val n = matrix.size
        for (layer in 0 until n / 2) {
            val last = n - 1 - layer
            for (offset in 0 until last - layer) {
                val top = matrix[layer][layer + offset]
                // left -> top, bottom -> left, right -> bottom, top -> right
                matrix[layer][layer + offset] = matrix[last - offset][layer]
                matrix[last - offset][layer] = matrix[last][last - offset]
                matrix[last][last - offset] = matrix[layer + offset][last]
                matrix[layer + offset][last] = top
            }
        }
    }
}
