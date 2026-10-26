class Solution {
    fun eraseOverlapIntervals(intervals: Array<IntArray>): Int {
        val ordered = intervals.sortedWith(compareBy<IntArray>({ it[0] }, { it[1] }))
        // longest[i]: the most intervals that can be kept among ordered[0..i], ending with ordered[i].
        val longest = IntArray(ordered.size)
        for (i in ordered.indices) {
            var best = 0
            for (j in 0 until i) {
                if (ordered[j][1] <= ordered[i][0]) {
                    best = maxOf(best, longest[j])
                }
            }
            longest[i] = best + 1
        }
        return intervals.size - longest.max()
    }
}
