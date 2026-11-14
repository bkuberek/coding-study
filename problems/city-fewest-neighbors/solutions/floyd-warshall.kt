// Large enough to never be a real distance, small enough that two of them do not overflow.
private const val FAR = Int.MAX_VALUE / 2

class Solution {
    fun findTheCity(n: Int, edges: Array<IntArray>, distanceThreshold: Int): Int {
        val dist = Array(n) { i -> IntArray(n) { j -> if (i == j) 0 else FAR } }
        for ((a, b, w) in edges) {
            dist[a][b] = w
            dist[b][a] = w
        }
        // After step m, dist[i][j] is the shortest route that only passes through cities 0..m.
        for (middle in 0 until n) {
            for (i in 0 until n) {
                for (j in 0 until n) {
                    dist[i][j] = minOf(dist[i][j], dist[i][middle] + dist[middle][j])
                }
            }
        }
        val counts = (0 until n).map { city -> (0 until n).count { it != city && dist[city][it] <= distanceThreshold } }
        val fewest = counts.min()
        // The last city with the smallest count wins ties.
        return (0 until n).last { counts[it] == fewest }
    }
}
