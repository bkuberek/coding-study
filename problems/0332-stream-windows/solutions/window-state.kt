import java.util.TreeMap

private const val KEYS = 1L shl 21

/** One number per (start, key), ordered by start and then key, since 0 <= key < KEYS. */
private fun window(start: Int, key: Int): Long = start * KEYS + key

private fun startOf(window: Long): Int = Math.floorDiv(window, KEYS).toInt()

private fun keyOf(window: Long): Int = Math.floorMod(window, KEYS).toInt()

private class Totals(var count: Int, var sum: Int)

/**
 * Every event is kept in a log, so the batch views of levels 1 and 2 can group the whole stream
 * in any way they are asked.
 *
 * The stream of levels 3 and 4 keeps a sorted map from (start, key) to a running count and sum
 * for the windows not yet emitted, and a second map for the windows already emitted that can
 * still be corrected. After each event the watermark moves, the open windows it has passed are
 * emitted in order, and the corrected windows it has left behind are forgotten.
 */
class StreamWindows {
    private data class Event(val key: Int, val time: Int, val value: Int)

    private val events = mutableListOf<Event>()
    private var size = 0
    private var lateness = 0
    private var grace = 0
    private var mark = 0
    private val open = TreeMap<Long, Totals>()
    private val closed = TreeMap<Long, Totals>()
    private var out = mutableListOf<List<Int>>()
    private val side = mutableListOf<List<Int>>()
    private var emitted = 0
    private var updated = 0

    // Level 1
    fun add(key: Int, time: Int, value: Int) {
        events.add(Event(key, time, value))
        if (size > 0) {
            stream(key, time, value)
        }
    }

    fun tumbling(size: Int): List<List<Int>> {
        val groups = TreeMap<Long, Totals>()
        for (e in events) {
            bump(groups, window(e.time - e.time % size, e.key), e.value)
        }
        return rows(groups, size)
    }

    // Level 2
    fun hopping(size: Int, slide: Int): List<List<Int>> {
        val groups = TreeMap<Long, Totals>()
        for (e in events) {
            var start = e.time - e.time % slide
            while (start > e.time - size) {
                bump(groups, window(start, e.key), e.value)
                start -= slide
            }
        }
        return rows(groups, size)
    }

    fun sessions(gap: Int): List<List<Int>> {
        val sessions = mutableListOf<IntArray>()
        for ((key, list) in events.groupBy { it.key }) {
            var current: IntArray? = null
            for (e in list.sortedBy { it.time }) {
                val session = current
                if (session != null && e.time < session[2]) {
                    session[2] = e.time + gap
                    session[3] += 1
                    session[4] += e.value
                } else {
                    current = intArrayOf(key, e.time, e.time + gap, 1, e.value).also { sessions.add(it) }
                }
            }
        }
        return sessions.sortedWith(compareBy({ it[1] }, { it[0] })).map { it.toList() }
    }

    // Level 3
    fun configure(size: Int, lateness: Int) {
        this.size = size
        this.lateness = lateness
    }

    fun watermark(): Int = mark

    fun pending(): List<List<Int>> = rows(open, size)

    fun poll(): List<List<Int>> {
        val result = out
        out = mutableListOf()
        return result
    }

    // Level 4
    fun allowUpdates(grace: Int) {
        this.grace = grace
    }

    fun dropped(): List<List<Int>> = side.toList()

    fun stats(): List<Int> = listOf(emitted, updated, side.size)

    // The stream
    private fun bump(groups: MutableMap<Long, Totals>, window: Long, value: Int) {
        val totals = groups.getOrPut(window) { Totals(0, 0) }
        totals.count += 1
        totals.sum += value
    }

    private fun row(window: Long, size: Int, count: Int, sum: Int): List<Int> {
        val start = startOf(window)
        return listOf(keyOf(window), start, start + size, count, sum)
    }

    private fun rows(groups: TreeMap<Long, Totals>, size: Int): List<List<Int>> =
        groups.map { (w, t) -> row(w, size, t.count, t.sum) }

    private fun stream(key: Int, time: Int, value: Int) {
        val start = time - time % size
        val end = start + size
        val w = window(start, key)
        when {
            end > mark -> bump(open, w, value)
            mark < end + grace -> correct(w, value)
            else -> side.add(listOf(key, time, value))
        }
        advance(time - lateness)
    }

    private fun correct(w: Long, value: Int) {
        val old = closed[w]
        if (old == null) {
            closed[w] = Totals(1, value)
            emitted += 1
            out.add(row(w, size, 1, value))
        } else {
            out.add(row(w, size, -old.count, -old.sum))
            old.count += 1
            old.sum += value
            updated += 1
            out.add(row(w, size, old.count, old.sum))
        }
    }

    private fun advance(candidate: Int) {
        if (candidate <= mark) {
            return
        }
        mark = candidate
        // A window is due when start + size <= mark, that is, when its number is below this bound.
        val due = open.headMap(window(mark - size + 1, 0))
        for ((w, totals) in due) {
            out.add(row(w, size, totals.count, totals.sum))
            closed[w] = totals
            emitted += 1
        }
        due.clear()
        closed.headMap(window(mark - size - grace + 1, 0)).clear()
    }
}
