class Solution {
    fun merge(intervals: Array<IntArray>): Array<IntArray> {
        var merged = listOf<IntArray>()
        for ((first, last) in intervals) {
            var start = first
            var end = last
            // Fold every merged interval that shares a point with [start, end] into it.
            val (overlapping, separate) = merged.partition { it[0] <= end && start <= it[1] }
            for (other in overlapping) {
                start = minOf(start, other[0])
                end = maxOf(end, other[1])
            }
            merged = separate + intArrayOf(start, end)
        }
        return merged.toTypedArray()
    }
}
