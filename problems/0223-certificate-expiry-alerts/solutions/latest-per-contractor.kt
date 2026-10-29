import java.time.LocalDate

class Solution {
    fun certificateAlerts(
        contractorIds: Array<String>,
        expiryDates: Array<LocalDate>,
        asOfDate: LocalDate,
        windowDays: Int,
    ): Array<Array<String>> {
        val latest = mutableMapOf<String, LocalDate>() // a renewal supersedes: only the latest expiry counts
        for ((i, contractor) in contractorIds.withIndex()) {
            latest[contractor] = maxOf(latest[contractor] ?: expiryDates[i], expiryDates[i])
        }
        val horizon = asOfDate.plusDays(windowDays.toLong())
        return latest.entries
            .filter { it.value <= horizon }
            .sortedWith(compareBy({ it.value }, { it.key }))
            .map { arrayOf(it.key, it.value.toString(), if (it.value <= asOfDate) "expired" else "expiring") }
            .toTypedArray()
    }
}
