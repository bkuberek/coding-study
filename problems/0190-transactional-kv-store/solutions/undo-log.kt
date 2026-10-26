import java.util.TreeMap

/** A permanent value from some sequence number on; null marks a removal. */
private data class PermanentValue(val value: String?)

class TransactionalStore {
    /** The current view, open transactions included. */
    private val data = HashMap<String, String>()
    private val counts = HashMap<String, Int>()

    /** One undo log per open transaction, innermost last: key to value before its first change. */
    private val undo = ArrayDeque<HashMap<String, String?>>()

    /** Permanent values per key, by the sequence number from which they hold. */
    private val history = HashMap<String, TreeMap<Int, PermanentValue>>()
    private var sequence = 0
    private val snapshots = mutableListOf<Int>()

    // Level 1
    fun set(timestamp: Long, key: String, value: String) = change(key, value)

    fun get(timestamp: Long, key: String): String = data[key] ?: ""

    fun remove(timestamp: Long, key: String): Boolean {
        if (key !in data) {
            return false
        }
        change(key, null)
        return true
    }

    fun count(timestamp: Long, value: String): Int = counts[value] ?: 0

    // Level 2
    fun begin(timestamp: Long) {
        undo.addLast(HashMap())
    }

    fun rollback(timestamp: Long): Boolean {
        val changed = undo.removeLastOrNull() ?: return false
        changed.forEach { (key, previous) -> assign(key, previous) }
        return true
    }

    // Level 3
    fun depth(timestamp: Long): Int = undo.size

    // Level 4
    fun commit(timestamp: Long): Int {
        val changed = undo.removeLastOrNull() ?: return -1
        val enclosing = undo.lastOrNull()
        if (enclosing != null) {
            // Not putIfAbsent: it would overwrite a key whose remembered value is null (absent).
            changed.forEach { (key, previous) ->
                if (key !in enclosing) {
                    enclosing[key] = previous
                }
            }
            return 0
        }
        makePermanent(changed.keys)
        snapshots += sequence
        return snapshots.size
    }

    fun getSnapshot(timestamp: Long, version: Int, key: String): String {
        val snapshot = snapshots.getOrNull(version - 1) ?: return ""
        return history[key]?.floorEntry(snapshot)?.value?.value ?: ""
    }

    private fun change(key: String, value: String?) {
        val innermost = undo.lastOrNull()
        if (innermost == null) {
            assign(key, value)
            makePermanent(listOf(key))
            return
        }
        if (key !in innermost) {
            innermost[key] = data[key]
        }
        assign(key, value)
    }

    private fun assign(key: String, value: String?) {
        val previous = if (value == null) data.remove(key) else data.put(key, value)
        previous?.let { counts.merge(it, -1, Int::plus) }
        value?.let { counts.merge(it, 1, Int::plus) }
    }

    private fun makePermanent(keys: Collection<String>) {
        sequence++
        for (key in keys) {
            history.getOrPut(key) { TreeMap() }[sequence] = PermanentValue(data[key])
        }
    }
}
