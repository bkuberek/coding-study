/**
 * Every triple ever recorded gets a number and a list of spans, the periods during which it was
 * present. Six hash indexes list the numbers by subject, predicate, object and the three pairs,
 * and one more finds a whole triple, so any pattern with a bound position starts from a short list
 * instead of a scan. Removing a triple only closes its span, so the history stays.
 *
 * A query joins its patterns one at a time, always taking the pattern whose candidate list is
 * shortest under the variables bound so far, and a path is a breadth-first walk with a visited
 * set, so a cycle ends the walk.
 */
class TripleStore {
    private class Span(val start: Long) {
        var end: Long = OPEN
        val names = ArrayList<String>()
        val times = ArrayList<Long>()
    }

    private class Found(val row: List<String>, val used: List<Int>)

    private class Match(val ends: List<String>, val id: Int)

    private val triples = ArrayList<List<String>>()
    private val spans = ArrayList<ArrayList<Span>>()
    private val exact = HashMap<String, Int>()
    private val byS = HashMap<String, ArrayList<Int>>()
    private val byP = HashMap<String, ArrayList<Int>>()
    private val byO = HashMap<String, ArrayList<Int>>()
    private val bySP = HashMap<String, ArrayList<Int>>()
    private val byPO = HashMap<String, ArrayList<Int>>()
    private val bySO = HashMap<String, ArrayList<Int>>()
    private var now = 0L
    private var live = 0

    // Level 1
    fun add(subject: String, predicate: String, obj: String): Boolean =
        record(subject, predicate, obj, "", now)

    fun remove(subject: String, predicate: String, obj: String): Boolean =
        retract(subject, predicate, obj, now)

    fun size(): Int = live

    fun match(subject: String, predicate: String, obj: String): List<List<String>> {
        val candidates = candidates(term(subject), term(predicate), term(obj))
        return each(candidates)
            .filter { present(it, CURRENT) }
            .map { triples[it] }
            .sortedWith { a, b -> compareRows(a, b) }
            .map { it.toList() }
    }

    // Level 2 and 3
    fun query(patterns: List<List<String>>, columns: List<String>): List<List<String>> =
        rows(patterns, columns, CURRENT, false).first

    // Level 4
    fun record(subject: String, predicate: String, obj: String, source: String, time: Long): Boolean {
        now = time
        val key = listOf(subject, predicate, obj).joinToString(SEP)
        val id = exact[key] ?: create(subject, predicate, obj, key)
        val history = spans[id]
        val last = history.lastOrNull()
        if (last != null && last.end == OPEN) {
            if (source.isNotEmpty() && source !in last.names) {
                last.names.add(source)
                last.times.add(time)
            }
            return false
        }
        val span = Span(time)
        if (source.isNotEmpty()) {
            span.names.add(source)
            span.times.add(time)
        }
        history.add(span)
        live++
        return true
    }

    fun retract(subject: String, predicate: String, obj: String, time: Long): Boolean {
        now = time
        val id = exact[listOf(subject, predicate, obj).joinToString(SEP)] ?: return false
        val last = spans[id].last()
        if (last.end != OPEN) return false
        last.end = time
        live--
        return true
    }

    fun queryAsOf(patterns: List<List<String>>, columns: List<String>, time: Long): List<List<String>> =
        rows(patterns, columns, time, false).first

    fun sourcesAsOf(patterns: List<List<String>>, columns: List<String>, time: Long): List<List<String>> =
        rows(patterns, columns, time, true).second

    // Storage
    private fun create(subject: String, predicate: String, obj: String, key: String): Int {
        val id = triples.size
        triples.add(listOf(subject, predicate, obj))
        spans.add(ArrayList())
        exact[key] = id
        byS.getOrPut(subject) { ArrayList() }.add(id)
        byP.getOrPut(predicate) { ArrayList() }.add(id)
        byO.getOrPut(obj) { ArrayList() }.add(id)
        bySP.getOrPut(subject + SEP + predicate) { ArrayList() }.add(id)
        byPO.getOrPut(predicate + SEP + obj) { ArrayList() }.add(id)
        bySO.getOrPut(subject + SEP + obj) { ArrayList() }.add(id)
        return id
    }

    private fun spanAt(id: Int, when_: Long): Span? {
        val history = spans[id]
        for (at in history.indices.reversed()) {
            val span = history[at]
            if (span.start <= when_) return if (when_ < span.end) span else null
        }
        return null
    }

    private fun present(id: Int, when_: Long): Boolean = spanAt(id, when_) != null

    private fun term(token: String): String? = if (token == "?") null else token

    /** The numbers of the triples that can match, from the narrowest index that applies; null means all. */
    private fun candidates(s: String?, p: String?, o: String?): List<Int>? {
        if (s != null && p != null && o != null) {
            val id = exact[listOf(s, p, o).joinToString(SEP)]
            return if (id == null) emptyList() else listOf(id)
        }
        return when {
            s != null && p != null -> bySP[s + SEP + p] ?: emptyList()
            p != null && o != null -> byPO[p + SEP + o] ?: emptyList()
            s != null && o != null -> bySO[s + SEP + o] ?: emptyList()
            s != null -> byS[s] ?: emptyList()
            p != null -> byP[p] ?: emptyList()
            o != null -> byO[o] ?: emptyList()
            else -> null
        }
    }

    private fun count(candidates: List<Int>?): Int = candidates?.size ?: triples.size

    private fun each(candidates: List<Int>?): List<Int> = candidates ?: triples.indices.toList()

    // Queries
    private fun rows(
        patterns: List<List<String>>,
        columns: List<String>,
        at: Long,
        track: Boolean,
    ): Pair<List<List<String>>, List<List<String>>> {
        val found = ArrayList<Found>()
        search(patterns, HashMap(), ArrayList(), columns, at, track, found)
        val distinct = HashMap<String, List<String>>()
        for (one in found) distinct[one.row.joinToString(SEP)] = one.row
        val rows = distinct.values.sortedWith { a, b -> compareRows(a, b) }
        if (!track) return Pair(rows, emptyList())
        val byRow = HashMap<String, java.util.TreeSet<String>>()
        for (row in rows) byRow[row.joinToString(SEP)] = java.util.TreeSet()
        for (one in found) {
            val names = byRow.getValue(one.row.joinToString(SEP))
            for (id in one.used) {
                val span = spanAt(id, at) ?: continue
                for (index in span.names.indices) {
                    if (span.times[index] <= at) names.add(span.names[index])
                }
            }
        }
        return Pair(rows, rows.map { byRow.getValue(it.joinToString(SEP)).toList() })
    }

    private fun search(
        remaining: List<List<String>>,
        bindings: HashMap<String, String>,
        used: ArrayList<Int>,
        columns: List<String>,
        at: Long,
        track: Boolean,
        found: ArrayList<Found>,
    ) {
        if (remaining.isEmpty()) {
            found.add(Found(columns.map { bindings.getValue(it) }, if (track) ArrayList(used) else emptyList()))
            return
        }
        var best = 0
        var bestCost = Long.MAX_VALUE
        for (index in remaining.indices) {
            val cost = cost(remaining[index], bindings)
            if (cost < bestCost) {
                bestCost = cost
                best = index
            }
        }
        val pattern = remaining[best]
        val rest = remaining.filterIndexed { index, _ -> index != best }
        for (one in matches(pattern, bindings, at)) {
            val undo = ArrayList<String>()
            if (unify(pattern, one.ends, bindings, undo)) {
                if (one.id >= 0) used.add(one.id)
                search(rest, bindings, used, columns, at, track, found)
                if (one.id >= 0) used.removeAt(used.size - 1)
            }
            for (name in undo) bindings.remove(name)
        }
    }

    private fun value(token: String, bindings: Map<String, String>): String? = when {
        token == "?" -> null
        token.startsWith("?") -> bindings[token]
        else -> token
    }

    private fun unify(
        pattern: List<String>,
        ends: List<String>,
        bindings: HashMap<String, String>,
        undo: ArrayList<String>,
    ): Boolean {
        val tokens = if (ends.size == 3) pattern else listOf(pattern[0], pattern[2])
        for (index in tokens.indices) {
            val token = tokens[index]
            if (token == "?") continue
            if (!token.startsWith("?")) {
                if (token != ends[index]) return false
            } else if (token in bindings) {
                if (bindings[token] != ends[index]) return false
            } else {
                bindings[token] = ends[index]
                undo.add(token)
            }
        }
        return true
    }

    private fun cost(pattern: List<String>, bindings: Map<String, String>): Long {
        val s = value(pattern[0], bindings)
        val p = value(pattern[1], bindings)
        val o = value(pattern[2], bindings)
        if (pattern[1].endsWith("+")) {
            if (s == null && o == null) return HUGE
            return (byP[pattern[1].dropLast(1)]?.size ?: 0).toLong()
        }
        return count(candidates(s, p, o)).toLong()
    }

    private fun matches(pattern: List<String>, bindings: Map<String, String>, at: Long): List<Match> {
        val s = value(pattern[0], bindings)
        val p = value(pattern[1], bindings)
        val o = value(pattern[2], bindings)
        if (pattern[1].endsWith("+")) {
            return pathPairs(s, pattern[1].dropLast(1), o, at).map { Match(it, -1) }
        }
        return each(candidates(s, p, o)).filter { present(it, at) }.map { Match(triples[it], it) }
    }

    private fun pathPairs(s: String?, p: String, o: String?, at: Long): List<List<String>> {
        if (s != null) {
            val reached = reach(s, p, true, at)
            if (o != null) return if (o in reached) listOf(listOf(s, o)) else emptyList()
            return reached.map { listOf(s, it) }
        }
        if (o != null) return reach(o, p, false, at).map { listOf(it, o) }
        val starts = LinkedHashSet<String>()
        for (id in byP[p].orEmpty()) {
            if (present(id, at)) starts.add(triples[id][0])
        }
        return starts.flatMap { start -> reach(start, p, true, at).map { listOf(start, it) } }
    }

    /** The nodes at the end of one or more hops; the start is in it only through a cycle. */
    private fun reach(start: String, p: String, forward: Boolean, at: Long): Set<String> {
        val seen = HashSet<String>()
        val queue = ArrayList<String>()
        queue.add(start)
        var next = 0
        while (next < queue.size) {
            val node = queue[next]
            val ids = if (forward) bySP[node + SEP + p] else byPO[p + SEP + node]
            for (id in ids.orEmpty()) {
                if (!present(id, at)) continue
                val following = if (forward) triples[id][2] else triples[id][0]
                if (seen.add(following)) queue.add(following)
            }
            next++
        }
        return seen
    }

    private fun compareRows(a: List<String>, b: List<String>): Int {
        for (index in a.indices) {
            val order = a[index].compareTo(b[index])
            if (order != 0) return order
        }
        return 0
    }

    private companion object {
        const val OPEN = (1L shl 53) - 1
        const val CURRENT = OPEN - 1
        const val HUGE = 1_000_000_000_000_000L
        const val SEP = "\u0000"
    }
}
