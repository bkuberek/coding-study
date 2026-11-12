class Solution {
    fun firstBadCommit(statuses: IntArray): IntArray {
        val firstBad = findFirstBad(statuses)
        val lastGood = findLastGoodBefore(statuses, firstBad)
        return intArrayOf(lastGood + 1, firstBad)
    }

    private fun findFirstBad(statuses: IntArray): Int {
        // Some commit is bad, so the first bad commit is somewhere in [low, high].
        var low = 0
        var high = statuses.size - 1
        while (low < high) {
            val middle = (low + high) ushr 1
            var probe = middle
            while (probe >= low && statuses[probe] == SKIP) probe--
            if (probe >= low && statuses[probe] == BAD) high = probe else low = middle + 1
        }
        return low
    }

    private fun findLastGoodBefore(statuses: IntArray, firstBad: Int): Int {
        // Before the first bad commit every commit that was tested is good. The last good one is
        // somewhere in [low, high], where -1 stands for "none".
        var low = -1
        var high = firstBad - 1
        while (low < high) {
            val middle = (low + high + 1) shr 1
            var probe = middle
            while (probe <= high && statuses[probe] == SKIP) probe++
            if (probe <= high) low = probe else high = middle - 1
        }
        return low
    }

    private companion object {
        const val BAD = 1
        const val SKIP = 2
    }
}
