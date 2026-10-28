import java.time.LocalDate

class Solution {
    fun coverageGaps(periods: Array<Array<LocalDate>>, windowStart: LocalDate, windowEnd: LocalDate): Array<Array<LocalDate>> {
        val gaps = ArrayList<Array<LocalDate>>()
        var cursor = windowStart // every day of the window before cursor is covered or already reported
        for ((start, end) in periods.sortedBy { it[0] }) {
            if (cursor >= windowEnd) break
            if (start > cursor) {
                gaps.add(arrayOf(cursor, minOf(start, windowEnd)))
            }
            cursor = maxOf(cursor, end)
        }
        if (cursor < windowEnd) {
            gaps.add(arrayOf(cursor, windowEnd))
        }
        return gaps.toTypedArray()
    }
}
