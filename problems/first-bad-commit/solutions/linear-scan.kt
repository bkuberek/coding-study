class Solution {
    fun firstBadCommit(statuses: IntArray): IntArray {
        var lastGood = -1
        for (position in statuses.indices) {
            when (statuses[position]) {
                0 -> lastGood = position
                1 -> return intArrayOf(lastGood + 1, position)
            }
        }
        throw IllegalArgumentException("the history has no bad commit")
    }
}
