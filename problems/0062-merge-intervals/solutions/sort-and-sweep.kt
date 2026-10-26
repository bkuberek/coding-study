class Solution {
    fun merge(intervals: Array<IntArray>): Array<IntArray> {
        val merged = ArrayList<IntArray>()
        for ((start, end) in intervals.sortedBy { it[0] }) {
            val last = merged.lastOrNull()
            if (last != null && start <= last[1]) {
                last[1] = maxOf(last[1], end)
            } else {
                merged.add(intArrayOf(start, end))
            }
        }
        return merged.toTypedArray()
    }
}
