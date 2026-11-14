class Solution {
    private val directions = arrayOf(intArrayOf(0, 1), intArrayOf(1, 0), intArrayOf(0, -1), intArrayOf(-1, 0))

    fun spiralOrder(matrix: Array<IntArray>): IntArray {
        val rows = matrix.size
        val cols = matrix[0].size
        val visited = Array(rows) { BooleanArray(cols) }
        val order = IntArray(rows * cols)
        var r = 0
        var c = 0
        var heading = 0
        for (step in order.indices) {
            order[step] = matrix[r][c]
            visited[r][c] = true
            var nr = r + directions[heading][0]
            var nc = c + directions[heading][1]
            if (nr !in 0 until rows || nc !in 0 until cols || visited[nr][nc]) {
                heading = (heading + 1) % 4
                nr = r + directions[heading][0]
                nc = c + directions[heading][1]
            }
            r = nr
            c = nc
        }
        return order
    }
}
