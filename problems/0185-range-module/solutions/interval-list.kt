class RangeModule {
    // Disjoint, non-touching half-open intervals (start, end), sorted by start.
    private var intervals = listOf<Pair<Int, Int>>()

    fun addRange(left: Int, right: Int) {
        var newStart = left
        var newEnd = right
        val merged = ArrayList<Pair<Int, Int>>(intervals.size + 1)
        var placed = false
        for ((start, end) in intervals) {
            when {
                end < newStart -> merged.add(start to end)
                newEnd < start -> {
                    if (!placed) {
                        merged.add(newStart to newEnd)
                        placed = true
                    }
                    merged.add(start to end)
                }
                else -> {
                    // Overlapping or touching: absorb it into the new interval.
                    newStart = minOf(newStart, start)
                    newEnd = maxOf(newEnd, end)
                }
            }
        }
        if (!placed) merged.add(newStart to newEnd)
        intervals = merged
    }

    // Stored intervals never touch, so a covered range lies inside a single one.
    fun queryRange(left: Int, right: Int): Boolean =
        intervals.any { (start, end) -> start <= left && right <= end }

    fun removeRange(left: Int, right: Int) {
        val kept = ArrayList<Pair<Int, Int>>(intervals.size + 1)
        for ((start, end) in intervals) {
            if (end <= left || right <= start) {
                kept.add(start to end)
                continue
            }
            if (start < left) kept.add(start to left)
            if (right < end) kept.add(right to end)
        }
        intervals = kept
    }
}
