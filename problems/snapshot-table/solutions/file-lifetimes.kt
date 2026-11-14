private const val NEVER = Int.MAX_VALUE

private class DataFile(val path: String, val partition: String, val rows: String, val added: Int) {
    var removed = NEVER

    fun liveAt(snapshot: Int): Boolean = snapshot in added until removed
}

private class Snapshot(val id: Int, val parent: Int, val timestamp: Long, val operation: String) {
    val added = mutableListOf<DataFile>()
    val removed = mutableListOf<DataFile>()
}

/**
 * Snapshots are numbered 1, 2, 3 in commit order, and history is a single line, so a data file is
 * live in one interval of snapshots: from the one that added it up to, not including, the one that
 * removed it. Each file keeps that interval, each snapshot keeps the files it added and removed,
 * and every question is a filter over the files or a walk over the snapshots.
 */
class SnapshotTable {
    private val files = HashMap<String, DataFile>()
    private val snapshots = mutableListOf<Snapshot>()
    private var firstRetained = 1

    // Level 1
    fun append(files: List<List<String>>, timestamp: Long): Int {
        if (files.isEmpty() || !fresh(files)) {
            return -1
        }
        return commitChange(files, emptyList(), timestamp, null)
    }

    fun currentSnapshot(): Int = snapshots.size

    fun scan(): List<String> = scanAt(currentSnapshot())

    fun manifest(snapshotId: Int): List<List<String>> {
        if (!retained(snapshotId)) {
            return emptyList()
        }
        return files.values.mapNotNull { file ->
            val status = when {
                file.liveAt(snapshotId) -> if (file.added == snapshotId) "added" else "existing"
                file.removed == snapshotId -> "deleted"
                else -> null
            }
            status?.let { listOf(file.path, file.partition, file.rows, it) }
        }.sortedBy { it[0] }
    }

    // Level 2
    fun deleteFiles(paths: List<String>, timestamp: Long): Int {
        if (paths.isEmpty() || !removable(paths, currentSnapshot())) {
            return -1
        }
        return commitChange(emptyList(), paths, timestamp, null)
    }

    fun overwrite(partition: String, files: List<List<String>>, timestamp: Long): Int {
        if (files.any { it[1] != partition } || !fresh(files)) {
            return -1
        }
        val current = currentSnapshot()
        val old = this.files.values.filter { it.partition == partition && it.liveAt(current) }.map { it.path }
        if (old.isEmpty() && files.isEmpty()) {
            return -1
        }
        return commitChange(files, old, timestamp, null)
    }

    fun scanAt(snapshotId: Int): List<String> {
        if (!retained(snapshotId)) {
            return emptyList()
        }
        return files.values.filter { it.liveAt(snapshotId) }.map { it.path }.sorted()
    }

    fun snapshotAsOf(timestamp: Long): Int {
        val found = snapshots.lastOrNull { it.timestamp <= timestamp }?.id ?: 0
        return if (found >= firstRetained) found else 0
    }

    fun history(): List<List<String>> =
        snapshots.drop(firstRetained - 1).map {
            listOf(
                it.id.toString(),
                it.parent.toString(),
                it.timestamp.toString(),
                it.operation,
                it.added.size.toString(),
                it.removed.size.toString(),
            )
        }

    // Level 3
    fun commit(base: Int, adds: List<List<String>>, removes: List<String>, timestamp: Long): List<String> {
        val current = currentSnapshot()
        val baseOk = (base == 0 && firstRetained == 1) || retained(base)
        if (!baseOk || (adds.isEmpty() && removes.isEmpty()) || !fresh(adds) || !removable(removes, base)) {
            return listOf("invalid", "")
        }
        val removing = removes.toSet()
        val partitions = removes.map { files.getValue(it).partition }.toSet()
        for (snapshot in snapshots.subList(base, current)) {
            val removedTwice = snapshot.removed.any { it.path in removing }
            val appended = snapshot.operation != "replace" && snapshot.added.any { it.partition in partitions }
            if (removedTwice || appended) {
                return listOf("conflict", snapshot.id.toString())
            }
        }
        val outcome = if (base == current) "committed" else "rebased"
        return listOf(outcome, commitChange(adds, removes, timestamp, null).toString())
    }

    // Level 4
    fun expireSnapshots(olderThan: Long, retainLast: Int): List<String> {
        val oldFirst = firstRetained
        val lastCandidate = currentSnapshot() - retainLast
        while (firstRetained <= lastCandidate && snapshots[firstRetained - 1].timestamp < olderThan) {
            firstRetained++
        }
        return files.values.filter { it.removed in (oldFirst + 1)..firstRetained }.map { it.path }.sorted()
    }

    fun compact(partition: String, maxFileRows: Int, timestamp: Long): Int {
        val current = currentSnapshot()
        val small = files.values.filter {
            it.partition == partition && it.liveAt(current) && it.rows.toLong() < maxFileRows
        }
        if (small.size < 2) {
            return -1
        }
        val rows = small.sumOf { it.rows.toLong() }
        val path = "$partition/compacted-${current + 1}"
        return commitChange(listOf(listOf(path, partition, rows.toString())), small.map { it.path }, timestamp, "replace")
    }

    // Helpers
    private fun retained(snapshotId: Int): Boolean = snapshotId in firstRetained..currentSnapshot()

    private fun fresh(adds: List<List<String>>): Boolean {
        val paths = adds.map { it[0] }
        return paths.toSet().size == paths.size && paths.none { it in files }
    }

    private fun removable(paths: List<String>, snapshotId: Int): Boolean =
        paths.toSet().size == paths.size && paths.all { files[it]?.liveAt(snapshotId) == true }

    private fun commitChange(adds: List<List<String>>, removes: List<String>, timestamp: Long, operation: String?): Int {
        val parent = currentSnapshot()
        val id = parent + 1
        val kind = operation ?: when {
            adds.isNotEmpty() && removes.isNotEmpty() -> "overwrite"
            adds.isNotEmpty() -> "append"
            else -> "delete"
        }
        val snapshot = Snapshot(id, parent, timestamp, kind)
        for (path in removes) {
            val file = files.getValue(path)
            file.removed = id
            snapshot.removed.add(file)
        }
        for ((path, partition, rows) in adds) {
            val file = DataFile(path, partition, rows, id)
            files[path] = file
            snapshot.added.add(file)
        }
        snapshots.add(snapshot)
        return id
    }
}
