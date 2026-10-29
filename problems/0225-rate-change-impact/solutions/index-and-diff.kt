import java.math.BigDecimal
import java.math.RoundingMode

class Solution {
    private class Change(val code: String, val percent: BigDecimal)

    fun rateChangeImpact(
        oldCodes: Array<String>,
        oldRates: Array<BigDecimal>,
        newCodes: Array<String>,
        newRates: Array<BigDecimal>,
    ): Array<Array<String>> {
        val old = oldCodes.zip(oldRates).toMap()
        val current = newCodes.zip(newRates).toMap()

        val changed = ArrayList<Change>()
        for ((code, rate) in current) {
            val before = old[code] ?: continue
            if (rate.compareTo(before) != 0) { // `!=` is equals(), which is scale-sensitive: 12.50 != 12.5
                // `/` would round half-even at the dividend's scale; divide with an explicit scale.
                val percent = ((rate - before) * BigDecimal(100)).divide(before, 2, RoundingMode.HALF_UP)
                changed.add(Change(code, percent))
            }
        }
        val added = current.keys.filter { it !in old }.sorted()
        val removed = old.keys.filter { it !in current }.sorted()

        // Numeric order of the rounded percent, largest first; ties by code.
        val ordered = changed.sortedWith(compareByDescending<Change> { it.percent }.thenBy { it.code })
        return (
            ordered.map { arrayOf(it.code, "changed", it.percent.toPlainString()) } +
                added.map { arrayOf(it, "added", "") } +
                removed.map { arrayOf(it, "removed", "") }
        ).toTypedArray()
    }
}
