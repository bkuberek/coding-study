private const val MOD = 1_000_000_007

class Solution {
    fun uniquePaths(m: Int, n: Int): Int {
        // routes[row][column] is the number of routes from the start to that cell. The first row
        // and the first column can only be reached in a straight line.
        val routes = Array(m) { IntArray(n) { 1 } }
        for (row in 1 until m) {
            for (column in 1 until n) {
                routes[row][column] = (routes[row - 1][column] + routes[row][column - 1]) % MOD
            }
        }
        return routes[m - 1][n - 1]
    }
}
