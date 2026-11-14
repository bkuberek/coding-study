private const val MOD = 1_000_000_007

class Solution {
    fun uniquePaths(m: Int, n: Int): Int {
        // routes[row][column] caches the number of routes from that cell to the goal; -1 is unknown.
        val routes = Array(m) { IntArray(n) { -1 } }

        fun count(row: Int, column: Int): Int {
            if (row == m - 1 || column == n - 1) return 1
            if (routes[row][column] < 0) {
                routes[row][column] = (count(row + 1, column) + count(row, column + 1)) % MOD
            }
            return routes[row][column]
        }

        return count(0, 0)
    }
}
