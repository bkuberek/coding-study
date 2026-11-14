/**
 * Every key keeps a chain of committed versions, oldest first, each stamped with the commit time of
 * its writer and the id of that writer (0 for a put). A transaction buffers its writes until it
 * commits, so the chains only ever hold committed data, and a read is a binary search for the
 * newest stamp before the reader's start. Serializable transactions also leave their reads behind,
 * even after they commit, and every read-write antidependency between two of them is kept as a
 * pair of edges. An edge stops counting as soon as either end aborts.
 */
class MvccStore {
    private class Transaction(val start: Int, val serializable: Boolean) {
        var state = "active"
        var commitTime = 0
        val writes = LinkedHashMap<String, String>()
        val ins = mutableSetOf<Int>()
        val outs = mutableSetOf<Int>()
    }

    private class Chain {
        val stamps = mutableListOf<Int>()
        val values = mutableListOf<String>()
        val writers = mutableListOf<Int>()

        /** The number of versions stamped before [time]. */
        fun before(time: Int): Int {
            val position = stamps.binarySearch(time)
            return if (position >= 0) position else -position - 1
        }
    }

    private var clock = 0
    private val chains = HashMap<String, Chain>()
    private val transactions = HashMap<Int, Transaction>()
    private val readers = HashMap<String, MutableSet<Int>>()

    // Level 1
    fun put(key: String, value: String): Int {
        clock++
        append(key, value, clock, 0)
        return clock
    }

    fun begin(): Int = start(false)

    fun read(tx: Int, key: String): String {
        val reader = active(tx) ?: return ""
        reader.writes[key]?.let { return it }
        if (reader.serializable && !recordRead(tx, reader, key)) return ""
        val chain = chains[key] ?: return ""
        val visible = chain.before(reader.start)
        return if (visible > 0) chain.values[visible - 1] else ""
    }

    fun versions(key: String): List<String> {
        val chain = chains[key] ?: return emptyList()
        return chain.stamps.indices.reversed().map { "${chain.stamps[it]}:${chain.values[it]}" }
    }

    // Level 2
    fun write(tx: Int, key: String, value: String): Boolean {
        val writer = active(tx) ?: return false
        if (writer.serializable && !recordWrite(tx, writer, key)) return false
        writer.writes[key] = value
        return true
    }

    fun commit(tx: Int): String {
        val t = active(tx) ?: return "not-active"
        if (t.writes.keys.any { (chains[it]?.stamps?.last() ?: 0) > t.start }) {
            t.state = "aborted"
            return "write-conflict"
        }
        if (t.serializable && live(t.ins).isNotEmpty() && live(t.outs).isNotEmpty()) {
            t.state = "aborted"
            return "dangerous-structure"
        }
        clock++
        t.state = "committed"
        t.commitTime = clock
        for ((key, value) in t.writes) append(key, value, clock, tx)
        return "committed"
    }

    fun abort(tx: Int): Boolean {
        val t = active(tx) ?: return false
        t.state = "aborted"
        return true
    }

    fun status(tx: Int): String = transactions[tx]?.state ?: "unknown"

    // Level 3
    fun beginSerializable(): Int = start(true)

    fun antidependencies(tx: Int): List<String> {
        val t = transactions[tx]
        if (t == null || t.state == "aborted") return emptyList()
        return live(t.ins).sorted().map { "in:$it" } + live(t.outs).sorted().map { "out:$it" }
    }

    // Level 4
    fun horizon(): Int =
        transactions.values.filter { it.state == "active" }.minOfOrNull { it.start } ?: clock

    fun vacuum(): List<String> {
        val limit = horizon()
        val removed = mutableListOf<String>()
        for (key in chains.keys.sorted()) {
            val chain = chains.getValue(key)
            val keepFrom = chain.before(limit + 1) - 1
            if (keepFrom <= 0) continue
            chain.stamps.subList(0, keepFrom).mapTo(removed) { "$key@$it" }
            chain.stamps.subList(0, keepFrom).clear()
            chain.values.subList(0, keepFrom).clear()
            chain.writers.subList(0, keepFrom).clear()
        }
        return removed
    }

    // Helpers
    private fun start(serializable: Boolean): Int {
        clock++
        transactions[clock] = Transaction(clock, serializable)
        return clock
    }

    private fun active(tx: Int): Transaction? = transactions[tx]?.takeIf { it.state == "active" }

    private fun append(key: String, value: String, stamp: Int, writer: Int) {
        val chain = chains.getOrPut(key) { Chain() }
        chain.stamps.add(stamp)
        chain.values.add(value)
        chain.writers.add(writer)
    }

    private fun takesPart(tx: Int): Boolean {
        val t = transactions[tx] ?: return false
        return t.serializable && t.state != "aborted"
    }

    private fun live(ids: Set<Int>): Set<Int> =
        ids.filterTo(HashSet()) { transactions.getValue(it).state != "aborted" }

    /**
     * The reader misses every version committed after it began and every write still buffered by
     * an active transaction: each such writer gets an edge from the reader.
     */
    private fun recordRead(tx: Int, reader: Transaction, key: String): Boolean {
        val committed = chains[key]
            ?.let { chain -> chain.writers.drop(chain.before(reader.start)).filter { takesPart(it) } }
            .orEmpty()
        if (committed.any { live(transactions.getValue(it).outs).isNotEmpty() }) {
            reader.state = "aborted"
            return false
        }
        val buffered = transactions.filter { (other, t) ->
            other != tx && t.serializable && t.state == "active" && key in t.writes
        }.keys
        readers.getOrPut(key) { mutableSetOf() }.add(tx)
        for (writer in committed + buffered) edge(tx, writer)
        return true
    }

    /** Every reader of the key that overlaps the writer gets an edge to it. */
    private fun recordWrite(tx: Int, writer: Transaction, key: String): Boolean {
        val overlapping = readers[key].orEmpty().filter { other ->
            val t = transactions.getValue(other)
            other != tx && takesPart(other) && (t.state == "active" || t.commitTime > writer.start)
        }
        val committedPivot = overlapping.any {
            val t = transactions.getValue(it)
            t.state == "committed" && live(t.ins).isNotEmpty()
        }
        if (committedPivot) {
            writer.state = "aborted"
            return false
        }
        for (reader in overlapping) edge(reader, tx)
        return true
    }

    private fun edge(reader: Int, writer: Int) {
        transactions.getValue(reader).outs.add(writer)
        transactions.getValue(writer).ins.add(reader)
    }
}
