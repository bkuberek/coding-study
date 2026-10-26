// Debug: Leaderboard Comparator. Some tests fail: find the bug and fix it.
import kotlin.math.abs

class Solution {
    fun rankPlayers(names: Array<String>, scores: IntArray): Array<String> {
        val order = names.indices.sortedWith { a, b ->
            if (abs(scores[a] - scores[b]) <= SCORE_EPSILON) {
                names[a].compareTo(names[b])
            } else {
                scores[b] - scores[a]
            }
        }
        return Array(order.size) { names[order[it]] }
    }

    private companion object {
        const val SCORE_EPSILON = 1
    }
}
