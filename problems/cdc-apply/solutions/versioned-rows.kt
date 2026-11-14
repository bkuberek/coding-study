private const val OK = "ok"
private const val SKIPPED = "skipped"
private const val NEVER = -1

/**
 * A map from key to row holds the table. A second map holds each key's version, the position at
 * which its last change became visible, and keeps it when the row is deleted: that tombstone is
 * what stops an old insert from bringing a deleted row back.
 *
 * A change is skipped when its position is not after the key's version, or not after the
 * snapshot the table started from. A transaction's changes wait in a buffer until its commit,
 * then run into an overlay, a small map of the rows they change, which is written into the table
 * only when every change worked.
 */
class ReplicaTable(columns: List<String>) {
    private data class Change(val op: String, val row: List<String>)

    private val names = columns.toMutableList()
    private var table = HashMap<String, MutableList<String>>()
    private var versions = HashMap<String, Int>()
    private var floor = 0
    private var schemaVersion = 0
    private val staged = HashMap<String, MutableList<Change>>()

    // Level 1
    fun apply(op: String, row: List<String>): String {
        val code = check(row[0] in table, op, row)
        if (code == OK) {
            if (op == "delete") table.remove(row[0]) else table[row[0]] = row.toMutableList()
        }
        return code
    }

    fun rows(): List<List<String>> = table.keys.sorted().map { table.getValue(it).toList() }

    // Level 2
    fun applyAt(lsn: Int, op: String, row: List<String>): String {
        val key = row[0]
        if (lsn <= floor || lsn <= version(key)) {
            return SKIPPED
        }
        val code = apply(op, row)
        if (code == OK) {
            versions[key] = lsn
        }
        return code
    }

    fun version(key: String): Int = versions[key] ?: NEVER

    // Level 3
    fun loadSnapshot(lsn: Int, snapshot: List<List<String>>) {
        table = HashMap(snapshot.associate { it[0] to it.toMutableList() })
        versions = HashMap(snapshot.associate { it[0] to lsn })
        floor = lsn
    }

    fun stage(tx: String, op: String, row: List<String>) {
        staged.getOrPut(tx) { mutableListOf() }.add(Change(op, row.toList()))
    }

    fun commit(lsn: Int, tx: String): String {
        val changes = staged.remove(tx).orEmpty()
        if (lsn <= floor) {
            return SKIPPED
        }
        // A key mapped to null was deleted by this transaction.
        val overlay = LinkedHashMap<String, List<String>?>()
        for ((op, row) in changes) {
            val key = row[0]
            if (lsn <= version(key)) {
                continue
            }
            val present = if (key in overlay) overlay[key] != null else key in table
            val code = check(present, op, row)
            if (code != OK) {
                return code
            }
            overlay[key] = if (op == "delete") null else row
        }
        if (overlay.isEmpty()) {
            return SKIPPED
        }
        for ((key, row) in overlay) {
            if (row == null) table.remove(key) else table[key] = row.toMutableList()
            versions[key] = lsn
        }
        return OK
    }

    fun rollback(tx: String) {
        staged.remove(tx)
    }

    // Level 4
    fun alterAt(lsn: Int, change: List<String>): String {
        if (lsn <= floor || lsn <= schemaVersion) {
            return SKIPPED
        }
        val code = alter(change)
        if (code == OK) {
            schemaVersion = lsn
        }
        return code
    }

    fun columns(): List<String> = names.toList()

    fun compare(sourceColumns: List<String>, sourceRows: List<List<String>>): List<List<String>> {
        val report = mutableListOf<List<String>>()
        for (name in (names + sourceColumns).toSortedSet()) {
            if (name !in names) {
                report.add(listOf("missing-column", name))
            } else if (name !in sourceColumns) {
                report.add(listOf("extra-column", name))
            }
        }
        val common = names.filter { it in sourceColumns }.sorted()
        val source = sourceRows.associateBy { it[0] }
        for (key in (table.keys + source.keys).toSortedSet()) {
            val here = table[key]
            val there = source[key]
            when {
                here == null -> report.add(listOf("missing-row", key))
                there == null -> report.add(listOf("extra-row", key))
                else -> for (name in common) {
                    val a = here[names.indexOf(name)]
                    val b = there[sourceColumns.indexOf(name)]
                    if (a != b) {
                        report.add(listOf("value-differs", key, name, a, b))
                    }
                }
            }
        }
        return report
    }

    // Changes
    private fun check(present: Boolean, op: String, row: List<String>): String = when {
        op != "delete" && row.size != names.size -> "column-count"
        op == "insert" -> if (present) "duplicate-key" else OK
        else -> if (present) OK else "unknown-key"
    }

    private fun alter(change: List<String>): String {
        val kind = change[0]
        val name = change[1]
        if (kind == "add") {
            if (name in names) {
                return "duplicate-column"
            }
            names.add(name)
            table.values.forEach { it.add(change[2]) }
            return OK
        }
        val index = names.indexOf(name)
        if (index < 0) {
            return "unknown-column"
        }
        if (kind == "drop") {
            if (index == 0) {
                return "key-column"
            }
            names.removeAt(index)
            table.values.forEach { it.removeAt(index) }
            return OK
        }
        if (change[2] in names) {
            return "duplicate-column"
        }
        names[index] = change[2]
        return OK
    }
}
