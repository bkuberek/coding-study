class Solution {
    fun rotate(matrix: Array<IntArray>) {
        val n = matrix.size
        // Row r of the rotated image is column r of the original, read from bottom to top.
        val rotated = Array(n) { r -> IntArray(n) { c -> matrix[n - 1 - c][r] } }
        for (r in 0 until n) {
            rotated[r].copyInto(matrix[r])
        }
    }
}
