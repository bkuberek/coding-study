import kotlin.math.floor
import kotlin.math.ln

private val ROW_CHECKS = setOf("not-null", "type", "allowed", "range", "unique", "references")
private val BATCH_CHECKS = setOf("row-count", "drift", "freshness")
private val ACTIONS = setOf("warn", "quarantine", "block")
private const val EMPTY_SHARE = 0.0001
private val DAYS_IN_MONTH = intArrayOf(31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)

private fun allDigits(text: String): Boolean = text.all { it in '0'..'9' }

private fun isInt(text: String): Boolean {
    val digits = text.removePrefix("-")
    return digits.length in 1..15 && allDigits(digits)
}

private fun isDate(text: String): Boolean {
    if (text.length != 10 || text[4] != '-' || text[7] != '-') {
        return false
    }
    val parts = listOf(text.substring(0, 4), text.substring(5, 7), text.substring(8, 10))
    if (!parts.all(::allDigits)) {
        return false
    }
    val (year, month, day) = parts.map { it.toInt() }
    if (year < 1 || month !in 1..12) {
        return false
    }
    val leap = year % 4 == 0 && (year % 100 != 0 || year % 400 == 0)
    val last = if (month == 2 && leap) 29 else DAYS_IN_MONTH[month - 1]
    return day in 1..last
}

/** A non-negative decimal with at most four places, in units of 0.0001. */
private fun tenThousandths(decimal: String): Long {
    val whole = decimal.substringBefore('.')
    val fraction = if ('.' in decimal) decimal.substringAfter('.') else ""
    return whole.toLong() * 10000 + (fraction + "0000").take(4).toLong()
}

private class Rule(
    val ruleId: String,
    val check: String,
    val columns: List<String>,
    val params: List<String>,
    var action: String = "block",
)

/**
 * Rules are data: each one is a check name, its columns and its parameters, kept in the order they
 * were added. Validation runs every rule over the rows and reports what failed; the gate runs the
 * row rules first, sets aside the rows that quarantine rules reject, and runs the batch rules on
 * what is left.
 */
class QualityGate(columns: List<String>) {
    private val index: Map<String, Int> = columns.withIndex().associate { it.value to it.index }
    private val rules = mutableListOf<Rule>()
    private val byId = HashMap<String, Rule>()
    private val dimensions = HashMap<String, Set<String>>()
    private var previous: List<List<String>>? = null
    private var now = 0L
    private var aside: List<Int> = emptyList()

    // Level 1
    fun addRule(ruleId: String, check: String, columns: List<String>, params: List<String>): Boolean {
        val known = check in ROW_CHECKS || check in BATCH_CHECKS
        if (ruleId in byId || !known || columns.any { it !in index }) {
            return false
        }
        if (check == "references" && params[0] !in dimensions) {
            return false
        }
        val rule = Rule(ruleId, check, columns.toList(), params.toList())
        rules.add(rule)
        byId[ruleId] = rule
        return true
    }

    fun validate(rows: List<List<String>>): List<List<String>> = rules.flatMap { findings(it, rows) }

    fun failingRows(rows: List<List<String>>, ruleId: String): List<Int> {
        val rule = byId[ruleId] ?: return emptyList()
        if (rule.check in BATCH_CHECKS) {
            return emptyList()
        }
        return rowFailures(rule, rows).flatMap { it.second }.toSortedSet().toList()
    }

    // Level 2
    fun loadDimension(name: String, keys: List<String>): Int {
        dimensions[name] = keys.toSet()
        return dimensions.getValue(name).size
    }

    fun setPreviousBatch(rows: List<List<String>>): Int {
        previous = rows.toList()
        return rows.size
    }

    // Level 3
    fun setTime(now: Long) {
        this.now = now
    }

    // Level 4
    fun setAction(ruleId: String, action: String): Boolean {
        val rule = byId[ruleId] ?: return false
        if (action !in ACTIONS || (action == "quarantine" && rule.check in BATCH_CHECKS)) {
            return false
        }
        rule.action = action
        return true
    }

    fun decide(rows: List<List<String>>): List<List<String>> {
        val setAside = sortedSetOf<Int>()
        for (rule in rules) {
            if (rule.check in ROW_CHECKS && rule.action == "quarantine") {
                setAside.addAll(failingRows(rows, rule.ruleId))
            }
        }
        val kept = rows.filterIndexed { at, _ -> at !in setAside }
        val findings = rules.flatMap { rule ->
            val seen = if (rule.check in ROW_CHECKS) rows else kept
            findings(rule, seen).map { it + rule.action }
        }
        if (findings.any { it[3] == "block" }) {
            aside = emptyList()
            return listOf(listOf("block", "0", "0")) + findings
        }
        aside = setAside.toList()
        previous = kept
        return listOf(listOf("publish", kept.size.toString(), setAside.size.toString())) + findings
    }

    fun quarantined(): List<Int> = aside.toList()

    // Helpers
    private fun findings(rule: Rule, rows: List<List<String>>): List<List<String>> {
        if (rule.check in ROW_CHECKS) {
            return rowFailures(rule, rows)
                .filter { it.second.isNotEmpty() }
                .map { (column, bad) -> listOf(rule.ruleId, column, bad.size.toString()) }
        }
        val observed = batchFailure(rule, rows) ?: return emptyList()
        return listOf(listOf(rule.ruleId, rule.columns.joinToString(""), observed))
    }

    /** For each column of a row rule (one joined key for unique), the rows that fail it. */
    private fun rowFailures(rule: Rule, rows: List<List<String>>): List<Pair<String, List<Int>>> {
        if (rule.check == "unique") {
            val groups = LinkedHashMap<String, MutableList<Int>>()
            rows.forEachIndexed { at, row ->
                val parts = rule.columns.map { row[index.getValue(it)] }
                if ("" !in parts) {
                    val key = parts.joinToString("") { "${it.length}:$it" }
                    groups.getOrPut(key) { mutableListOf() }.add(at)
                }
            }
            val bad = groups.values.filter { it.size > 1 }.flatten().sorted()
            return listOf(rule.columns.joinToString("+") to bad)
        }
        return rule.columns.map { column ->
            val at = index.getValue(column)
            column to rows.indices.filter { fails(rule, rows[it][at]) }
        }
    }

    private fun fails(rule: Rule, value: String): Boolean {
        if (rule.check == "not-null") {
            return value.isEmpty()
        }
        if (value.isEmpty()) {
            return false
        }
        return when (rule.check) {
            "type" -> !(if (rule.params[0] == "int") isInt(value) else isDate(value))
            "allowed" -> value !in rule.params
            "range" -> isInt(value) && value.toLong() !in rule.params[0].toLong()..rule.params[1].toLong()
            else -> value !in dimensions.getValue(rule.params[0])
        }
    }

    /** The observed value of a failing batch rule, or null when it passes. */
    private fun batchFailure(rule: Rule, rows: List<List<String>>): String? {
        val before = previous
        if (rule.check == "row-count") {
            if (before == null) {
                return null
            }
            val tolerance = rule.params[0].toLong()
            val low = before.size * (100 - tolerance) / 100
            val high = (before.size * (100 + tolerance) + 99) / 100
            return if (rows.size.toLong() in low..high) null else rows.size.toString()
        }
        val column = index.getValue(rule.columns[0])
        val values = integers(rows, column)
        if (rule.check == "freshness") {
            if (values.isEmpty()) {
                return "none"
            }
            val lag = now - values.max()
            return if (lag > rule.params[0].toLong()) lag.toString() else null
        }
        if (before == null) {
            return null
        }
        val baseline = integers(before, column)
        if (values.isEmpty() || baseline.isEmpty()) {
            return null
        }
        val edges = rule.params.drop(1).map { it.toLong() }
        val units = floor(psi(values, baseline, edges) * 10000 + 0.5).toLong()
        if (units < tenThousandths(rule.params[0])) {
            return null
        }
        return "${units / 10000}.${(units % 10000).toString().padStart(4, '0')}"
    }

    private fun integers(rows: List<List<String>>, column: Int): List<Long> =
        rows.filter { isInt(it[column]) }.map { it[column].toLong() }

    private fun psi(values: List<Long>, baseline: List<Long>, edges: List<Long>): Double {
        val actual = shares(values, edges)
        val expected = shares(baseline, edges)
        var total = 0.0
        for (bin in actual.indices) {
            total += (actual[bin] - expected[bin]) * ln(actual[bin] / expected[bin])
        }
        return total
    }

    private fun shares(sample: List<Long>, edges: List<Long>): DoubleArray {
        val counts = IntArray(edges.size + 1)
        for (value in sample) {
            counts[binOf(value, edges)]++
        }
        return DoubleArray(counts.size) { if (counts[it] == 0) EMPTY_SHARE else counts[it].toDouble() / sample.size }
    }

    /** The number of edges at or below the value. */
    private fun binOf(value: Long, edges: List<Long>): Int {
        var low = 0
        var high = edges.size
        while (low < high) {
            val middle = (low + high) ushr 1
            if (edges[middle] <= value) low = middle + 1 else high = middle
        }
        return low
    }
}
