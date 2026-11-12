/**
 * Every counter keeps its samples in time order. The increase over a window walks the samples
 * inside it and adds each step, counting a drop as a restart from zero. A histogram is one such
 * counter per bucket. SLOs, burn rates and alerts are ratios of increases, kept as exact fractions
 * and compared by cross-multiplying.
 */
class SloMonitor {
    private class Slo(val good: String, val total: String, val met: Long, val outOf: Long, val window: Long) {
        val spare get() = outOf - met
    }

    private class Alert(val severity: String, val longWindow: Long, val shortWindow: Long, val above: Long, val below: Long)

    private val times = HashMap<String, MutableList<Long>>()
    private val values = HashMap<String, MutableList<Long>>()
    private val bounds = HashMap<String, List<Long>>()
    private val slos = HashMap<String, Slo>()
    private val alerts = HashMap<String, MutableList<Alert>>()

    // Level 1
    fun scrape(series: String, timestamp: Long, value: Long): String {
        val seen = times.getOrPut(series) { ArrayList() }
        if (seen.isNotEmpty() && timestamp <= seen.last()) return "out-of-order"
        seen.add(timestamp)
        values.getOrPut(series) { ArrayList() }.add(value)
        return "ok"
    }

    fun scrapeSeries(series: String, start: Long, step: Long, values: List<Long>): Int =
        values.withIndex().count { (i, value) -> scrape(series, start + i * step, value) == "ok" }

    fun increase(series: String, start: Long, end: Long): Long {
        val got = window(series, start, end, values)
        if (got.size < 2) return -1
        return got.zipWithNext { before, after -> if (after >= before) after - before else after }.sum()
    }

    fun rate(series: String, start: Long, end: Long): String {
        val got = window(series, start, end, times)
        if (got.size < 2) return ""
        return fraction(increase(series, start, end), got.last() - got.first())
    }

    fun resets(series: String, start: Long, end: Long): Int =
        window(series, start, end, values).zipWithNext().count { (before, after) -> after < before }

    // Level 2
    fun scrapeHistogram(name: String, timestamp: Long, bounds: List<Long>, counts: List<Long>): String {
        val seen = times["$name:le=inf"].orEmpty()
        if (seen.isNotEmpty() && timestamp <= seen.last()) return "out-of-order"
        this.bounds[name] = bounds.toList()
        bounds.forEachIndexed { i, bound -> scrape("$name:le=$bound", timestamp, counts[i]) }
        scrape("$name:le=inf", timestamp, counts[bounds.size])
        return "ok"
    }

    fun fractionWithin(name: String, threshold: Long, start: Long, end: Long): String {
        val counts = buckets(name, start, end) ?: return ""
        val index = bounds.getValue(name).indexOf(threshold)
        return if (index < 0) "" else fraction(counts[index], counts.last())
    }

    fun quantile(name: String, q: String, start: Long, end: Long): String {
        val counts = buckets(name, start, end) ?: return ""
        val (top, bottom) = parseFraction(q)
        val limits = bounds.getValue(name)
        val total = counts.last()
        // The rank is q * total; the first bucket whose count reaches it holds the quantile.
        val index = counts.indexOfFirst { it * bottom >= top * total }
        if (index == limits.size) return limits.last().toString()
        val lower = if (index > 0) limits[index - 1] else 0L
        val before = if (index > 0) counts[index - 1] else 0L
        val inside = counts[index] - before
        val numerator = lower * bottom * inside + (limits[index] - lower) * (top * total - bottom * before)
        return fraction(numerator, bottom * inside)
    }

    // Level 3
    fun defineSlo(name: String, goodSeries: String, totalSeries: String, objective: String, window: Long): String {
        if (name in slos) return "duplicate"
        val (met, outOf) = parseFraction(objective)
        if (met <= 0 || met >= outOf) return "bad-objective"
        slos[name] = Slo(goodSeries, totalSeries, met, outOf, window)
        alerts[name] = ArrayList()
        return "ok"
    }

    fun sli(name: String, at: Long): String {
        val slo = slos[name] ?: return ""
        val (bad, total) = counts(slo, at, slo.window) ?: return ""
        return fraction(total - bad, total)
    }

    fun budgetRemaining(name: String, at: Long): String {
        val slo = slos[name] ?: return ""
        val (numerator, denominator) = left(slo, at) ?: return ""
        return fraction(numerator, denominator)
    }

    fun burnRate(name: String, at: Long, lookback: Long): String {
        val slo = slos[name] ?: return ""
        val (bad, total) = counts(slo, at, lookback) ?: return ""
        return fraction(bad * slo.outOf, total * slo.spare)
    }

    fun timeToExhaustion(name: String, at: Long, lookback: Long): Long {
        val slo = slos[name] ?: return -1
        val (leftOver, _) = left(slo, at) ?: return -1
        if (leftOver <= 0) return 0
        val (recentBad, recentTotal) = counts(slo, at, lookback) ?: return -1
        if (recentBad == 0L) return -1
        val (bad, total) = counts(slo, at, slo.window)!!
        // remaining * window / burn rate, with every product below 2^63.
        val numerator = slo.window * (total * slo.spare - bad * slo.outOf) * recentTotal
        return numerator / (total * recentBad * slo.outOf)
    }

    // Level 4
    fun addAlert(slo: String, severity: String, longWindow: Long, shortWindow: Long, threshold: String): String {
        val list = alerts[slo] ?: return "unknown-slo"
        if (list.any { it.severity == severity }) return "duplicate"
        if (longWindow <= 0 || shortWindow < 0 || shortWindow >= longWindow) return "bad-windows"
        val (above, below) = parseFraction(threshold)
        list.add(Alert(severity, longWindow, shortWindow, above, below))
        return "ok"
    }

    fun firing(slo: String, at: Long): List<String> {
        val target = slos[slo] ?: return emptyList()
        return alerts.getValue(slo).filter { fires(target, it, at) }.map { it.severity }
    }

    fun timeline(slo: String, start: Long, end: Long, step: Long): List<String> {
        val target = slos[slo] ?: return emptyList()
        val list = alerts.getValue(slo)
        val state = BooleanArray(list.size)
        val events = ArrayList<String>()
        var at = start
        while (at <= end) {
            list.forEachIndexed { i, alert ->
                val now = fires(target, alert, at)
                if (now != state[i]) {
                    events.add("$at ${alert.severity} ${if (now) "start" else "stop"}")
                    state[i] = now
                }
            }
            at += step
        }
        return events
    }

    // Helpers
    private tailrec fun gcd(a: Long, b: Long): Long = if (b == 0L) Math.abs(a) else gcd(b, a % b)

    /** `p/q` in lowest terms with q > 0, or `p` for a whole number. */
    private fun fraction(numerator: Long, denominator: Long): String {
        val sign = if (denominator < 0) -1 else 1
        val common = gcd(numerator, denominator)
        val top = sign * numerator / common
        val bottom = sign * denominator / common
        return if (bottom == 1L) top.toString() else "$top/$bottom"
    }

    private fun parseFraction(text: String): Pair<Long, Long> =
        if ('/' in text) text.substringBefore('/').toLong() to text.substringAfter('/').toLong() else text.toLong() to 1L

    /** The part of [column] (the times or the values of the series) inside the window. */
    private fun window(series: String, start: Long, end: Long, column: Map<String, List<Long>>): List<Long> {
        val seen = times[series].orEmpty()
        val low = seen.binarySearch { if (it < start) -1 else 1 }.let { -(it + 1) }
        val high = seen.binarySearch { if (it <= end) -1 else 1 }.let { -(it + 1) }
        return column[series].orEmpty().subList(low, maxOf(low, high))
    }

    /** The increase of every bucket over the window, or null when the window has no requests. */
    private fun buckets(name: String, start: Long, end: Long): List<Long>? {
        val limits = bounds[name] ?: return null
        val counts = (limits.map { it.toString() } + "inf").map { increase("$name:le=$it", start, end) }
        return if (counts.last() > 0) counts else null
    }

    /** (bad, total) over [at - span, at], or null without requests. */
    private fun counts(slo: Slo, at: Long, span: Long): Pair<Long, Long>? {
        val total = increase(slo.total, at - span, at)
        val good = increase(slo.good, at - span, at)
        if (total <= 0 || good < 0) return null
        return total - good to total
    }

    /** The share of the budget left, as (numerator, denominator). */
    private fun left(slo: Slo, at: Long): Pair<Long, Long>? {
        val (bad, total) = counts(slo, at, slo.window) ?: return null
        return total * slo.spare - bad * slo.outOf to total * slo.spare
    }

    private fun burnsAbove(slo: Slo, at: Long, span: Long, alert: Alert): Boolean {
        val (bad, total) = counts(slo, at, span) ?: return false
        return bad * slo.outOf * alert.below > alert.above * total * slo.spare
    }

    private fun fires(slo: Slo, alert: Alert, at: Long): Boolean =
        burnsAbove(slo, at, alert.longWindow, alert) &&
            (alert.shortWindow == 0L || burnsAbove(slo, at, alert.shortWindow, alert))
}
