private const val MOD = 1_000_000_007

class Solution {
    fun uniquePaths(m: Int, n: Int): Int {
        // Transposing the grid does not change the count, so keep the row along the shorter side.
        val width = minOf(m, n)
        val height = maxOf(m, n)
        // Before the update, routes[column] belongs to the row above; after it, to the current row.
        val routes = IntArray(width) { 1 }
        repeat(height - 1) {
            for (column in 1 until width) {
                routes[column] = (routes[column] + routes[column - 1]) % MOD
            }
        }
        return routes[width - 1]
    }
}
