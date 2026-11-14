import java.math.BigDecimal
import java.time.LocalDate

class RateTable {
    private class Version(val id: Int, val rates: Map<String, BigDecimal>)

    private companion object {
        val NOT_FOUND: BigDecimal = BigDecimal.ONE.negate()
    }

    // Parallel lists sorted by effective date; equal dates stay in publish order.
    private val dates = ArrayList<LocalDate>()
    private val versions = ArrayList<Version>()
    private var published = 0

    fun publish(effectiveDate: LocalDate, classCodes: Array<String>, rates: Array<BigDecimal>) {
        published++
        val slot = versionsOnOrBefore(effectiveDate)
        // A fresh map, so a published version never changes afterwards.
        dates.add(slot, effectiveDate)
        versions.add(slot, Version(published, classCodes.zip(rates).toMap()))
    }

    fun rateAsOf(onDate: LocalDate, classCode: String): BigDecimal {
        val slot = versionsOnOrBefore(onDate)
        if (slot == 0) return NOT_FOUND
        return versions[slot - 1].rates[classCode] ?: NOT_FOUND
    }

    fun versionAsOf(onDate: LocalDate): Int {
        val slot = versionsOnOrBefore(onDate)
        return if (slot > 0) versions[slot - 1].id else -1
    }

    // Number of versions effective on or before the day (upper bound). binarySearch may return
    // any of several equal dates, so the search is written out.
    private fun versionsOnOrBefore(day: LocalDate): Int {
        var low = 0
        var high = dates.size
        while (low < high) {
            val middle = (low + high) ushr 1
            if (dates[middle] <= day) low = middle + 1 else high = middle
        }
        return low
    }
}
