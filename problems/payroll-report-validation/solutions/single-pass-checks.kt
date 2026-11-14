import java.math.BigDecimal
import java.time.LocalDate

private val FIELDS = listOf("contractorId", "classCode", "payroll", "periodStart")

// [0-9], written out: the digits are ASCII only.
private val CONTRACTOR_ID = Regex("[a-z0-9-]{1,20}")
private val CLASS_CODE = Regex("[0-9]{4}")
private val PAYROLL = Regex("[0-9]+(\\.[0-9]{1,2})?")
private val ISO_DAY = Regex("[0-9]{4}-[0-9]{2}-[0-9]{2}")
private val MAX_PAYROLL = BigDecimal(1_000_000_000)
private val FIRST_DAY = LocalDate.of(2000, 1, 1)
private val LAST_DAY = LocalDate.of(2099, 12, 31)

class Solution {
    fun validateRows(rows: Array<Array<String>>): List<String> = buildList {
        val seenKeys = hashSetOf<Triple<String, String, String>>()
        for ((index, row) in rows.withIndex()) {
            if (row.size != FIELDS.size) {
                add("$index:row:column-count")
                continue
            }
            val reasons = listOf(
                checkPattern(row[0], CONTRACTOR_ID),
                checkPattern(row[1], CLASS_CODE),
                checkPayroll(row[2]),
                checkPeriodStart(row[3]),
            )
            for ((column, reason) in reasons.withIndex()) {
                if (reason.isNotEmpty()) add("$index:${FIELDS[column]}:$reason")
            }
            if (reasons[0].isEmpty() && reasons[1].isEmpty() && reasons[3].isEmpty()) {
                // add() returns false when the key was already there.
                if (!seenKeys.add(Triple(row[0], row[1], row[3]))) add("$index:row:duplicate")
            }
        }
    }

    private fun checkPattern(value: String, pattern: Regex): String = when {
        value.isEmpty() -> "missing"
        pattern.matches(value) -> ""
        else -> "invalid"
    }

    private fun checkPayroll(value: String): String {
        val reason = checkPattern(value, PAYROLL)
        if (reason.isNotEmpty()) return reason
        val amount = BigDecimal(value)
        return if (amount.signum() > 0 && amount <= MAX_PAYROLL) "" else "out-of-range"
    }

    private fun checkPeriodStart(value: String): String {
        val reason = checkPattern(value, ISO_DAY)
        if (reason.isNotEmpty()) return reason
        // Strict parse: 2026-02-30 fails instead of rolling over.
        val day = runCatching { LocalDate.parse(value) }.getOrNull() ?: return "invalid"
        if (day.year < 1) return "invalid" // LocalDate accepts year 0, but real days start in year 1
        return if (day < FIRST_DAY || day > LAST_DAY) "out-of-range" else ""
    }
}
