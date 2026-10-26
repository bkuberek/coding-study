private val STEPS = arrayOf(1 to 0, -1 to 0, 0 to 1, 0 to -1)

class Solution {
    fun longestIncreasingPath(matrix: Array<IntArray>): Int {
        val rows = matrix.size
        val columns = matrix[0].size

        fun neighbors(r: Int, c: Int): List<Pair<Int, Int>> =
            STEPS.map { (dr, dc) -> r + dr to c + dc }.filter { (nr, nc) -> nr in 0 until rows && nc in 0 until columns }

        // larger[r][c] counts the neighbors a path could still step up to from (r, c).
        val larger = Array(rows) { r ->
            IntArray(columns) { c -> neighbors(r, c).count { (nr, nc) -> matrix[nr][nc] > matrix[r][c] } }
        }
        // Kahn's algorithm from the sinks: each round removes the cells whose larger neighbors are
        // all gone. A cell removed in round k starts a longest path of exactly k cells.
        var layer = (0 until rows).flatMap { r -> (0 until columns).map { c -> r to c } }
            .filter { (r, c) -> larger[r][c] == 0 }
        var rounds = 0
        while (layer.isNotEmpty()) {
            rounds++
            val nextLayer = mutableListOf<Pair<Int, Int>>()
            for ((r, c) in layer) {
                for ((nr, nc) in neighbors(r, c)) {
                    if (matrix[nr][nc] < matrix[r][c] && --larger[nr][nc] == 0) {
                        nextLayer.add(nr to nc)
                    }
                }
            }
            layer = nextLayer
        }
        return rounds
    }
}
