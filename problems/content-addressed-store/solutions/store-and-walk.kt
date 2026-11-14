import java.io.ByteArrayOutputStream
import java.security.MessageDigest

private const val FIXED_SIZE = 64
private const val WINDOW = 16
private const val BASE = 257L
private const val MODULUS = 1_000_000_007L
private const val MIN_CHUNK = 32
private const val MAX_CHUNK = 256
private const val DIVISOR = 64L
private val KINDS = setOf("blob", "tree", "manifest")

private data class Entry(val kind: String, val address: String)

private class Damaged(address: String) : RuntimeException(address)

private fun addressOf(data: ByteArray): String =
    MessageDigest.getInstance("SHA-256").digest(data).joinToString("") { "%02x".format(it) }

private fun lines(data: ByteArray): List<String> {
    val text = data.toString(Charsets.UTF_8)
    return if (text.isEmpty()) emptyList() else text.dropLast(1).split("\n")
}

private fun fixedSizes(length: Int): List<Int> =
    (0 until length step FIXED_SIZE).map { start -> minOf(FIXED_SIZE, length - start) }

/** Content-defined cuts: a rolling hash of the last 16 bytes, rolled once per byte. */
private fun cdcSizes(data: ByteArray): List<Int> {
    var leavingWeight = 1L
    repeat(WINDOW - 1) { leavingWeight = leavingWeight * BASE % MODULUS }
    val sizes = mutableListOf<Int>()
    var windowHash = 0L
    var start = 0
    for (index in data.indices) {
        if (index >= WINDOW) {
            val leaving = (data[index - WINDOW].toLong() and 0xff) * leavingWeight
            windowHash = (windowHash - leaving).mod(MODULUS)
        }
        windowHash = (windowHash * BASE + (data[index].toLong() and 0xff)) % MODULUS
        val length = index - start + 1
        if (length == MAX_CHUNK || (length >= MIN_CHUNK && windowHash % DIVISOR == 0L)) {
            sizes += length
            start = index + 1
        }
    }
    if (start < data.size) {
        sizes += data.size - start
    }
    return sizes
}

/**
 * Objects are bytes filed under the SHA-256 digest of those bytes. Every read hashes what it finds
 * again, so a damaged object reads as a missing one. Folders and manifests are objects that list
 * other objects by address, and refs name the objects the collector keeps.
 */
class ContentStore {
    private val objects = mutableMapOf<String, ByteArray>()
    private val fileBytes = mutableMapOf("fixed" to 0L, "cdc" to 0L)
    private val chunks = mapOf("fixed" to mutableMapOf<String, Int>(), "cdc" to mutableMapOf())
    private val refs = mutableMapOf<String, Entry>()

    private fun write(data: ByteArray): String {
        val address = addressOf(data)
        if (read(address) == null) {
            objects[address] = data
        }
        return address
    }

    private fun read(address: String): ByteArray? =
        objects[address]?.takeIf { addressOf(it) == address }

    // Level 1
    fun put(data: String): String = write(data.toByteArray(Charsets.UTF_8))

    fun get(address: String): String = read(address)?.toString(Charsets.UTF_8) ?: ""

    fun check(address: String): String =
        when {
            address !in objects -> "missing"
            read(address) == null -> "damaged"
            else -> "ok"
        }

    fun damage(address: String, data: String): Boolean {
        if (address !in objects) {
            return false
        }
        objects[address] = data.toByteArray(Charsets.UTF_8)
        return true
    }

    fun count(): Int = objects.size

    fun bytesStored(): Int = objects.values.sumOf { it.size }

    // Level 2
    fun snapshot(files: List<List<String>>): String =
        folder(files.map { (path, data) -> path.split("/") to data })

    private fun folder(files: List<Pair<List<String>, String>>): String {
        val entries = mutableMapOf<String, Entry>()
        val below = linkedMapOf<String, MutableList<Pair<List<String>, String>>>()
        for ((names, data) in files) {
            if (names.size == 1) {
                entries[names[0]] = Entry("blob", put(data))
            } else {
                below.getOrPut(names[0]) { mutableListOf() } += names.drop(1) to data
            }
        }
        for ((name, inner) in below) {
            entries[name] = Entry("tree", folder(inner))
        }
        val text = entries.toSortedMap().entries.joinToString("") { (name, entry) ->
            "${entry.kind} ${entry.address} $name\n"
        }
        return put(text)
    }

    private fun openTree(address: String): Map<String, Entry> {
        val data = read(address) ?: throw Damaged(address)
        return lines(data).associate { line ->
            line.substring(70) to Entry(line.substring(0, 4), line.substring(5, 69))
        }
    }

    fun readPath(root: String, path: String): String {
        var entry = Entry("tree", root)
        try {
            for (name in path.split("/")) {
                if (entry.kind != "tree") {
                    return ""
                }
                entry = openTree(entry.address)[name] ?: return ""
            }
        } catch (e: Damaged) {
            return ""
        }
        return if (entry.kind == "blob") get(entry.address) else ""
    }

    fun diff(oldRoot: String, newRoot: String): List<String> {
        val changes = mutableListOf<Pair<String, String>>()
        try {
            compare("", oldRoot, newRoot, changes)
        } catch (e: Damaged) {
            return emptyList()
        }
        return changes.sortedBy { it.first }.map { (path, op) -> "$op $path" }
    }

    private fun compare(
        prefix: String,
        oldTree: String,
        newTree: String,
        changes: MutableList<Pair<String, String>>,
    ) {
        if (oldTree == newTree) {
            return
        }
        val before = openTree(oldTree)
        val after = openTree(newTree)
        for (name in before.keys + after.keys) {
            val path = prefix + name
            val was = before[name]
            val now = after[name]
            when {
                was == now -> continue
                was != null && now != null && was.kind == now.kind ->
                    if (was.kind == "blob") {
                        changes += path to "M"
                    } else {
                        compare("$path/", was.address, now.address, changes)
                    }
                else -> {
                    was?.let { listFiles("D", path, it, changes) }
                    now?.let { listFiles("A", path, it, changes) }
                }
            }
        }
    }

    private fun listFiles(
        op: String,
        path: String,
        entry: Entry,
        changes: MutableList<Pair<String, String>>,
    ) {
        if (entry.kind == "blob") {
            changes += path to op
            return
        }
        for ((name, inner) in openTree(entry.address)) {
            listFiles(op, "$path/$name", inner, changes)
        }
    }

    // Level 3
    fun chunkSizes(data: String, method: String): List<Int> {
        val raw = data.toByteArray(Charsets.UTF_8)
        return if (method == "fixed") fixedSizes(raw.size) else cdcSizes(raw)
    }

    fun putFile(data: String, method: String): String {
        val raw = data.toByteArray(Charsets.UTF_8)
        val seen = chunks.getValue(method)
        val manifest = StringBuilder()
        var start = 0
        for (size in chunkSizes(data, method)) {
            val address = write(raw.copyOfRange(start, start + size))
            seen[address] = size
            manifest.append(address).append('\n')
            start += size
        }
        fileBytes[method] = fileBytes.getValue(method) + raw.size
        return put(manifest.toString())
    }

    fun readFile(manifest: String): String {
        val listing = read(manifest) ?: return ""
        val parts = ByteArrayOutputStream()
        for (address in lines(listing)) {
            parts.write(read(address) ?: return "")
        }
        return parts.toString(Charsets.UTF_8)
    }

    fun dedupRatio(method: String): Double {
        val stored = chunks.getValue(method).values.sumOf { it.toLong() }
        return if (stored == 0L) 0.0 else fileBytes.getValue(method).toDouble() / stored
    }

    // Level 4
    fun setRef(name: String, kind: String, address: String): Boolean {
        if (kind !in KINDS || address !in objects) {
            return false
        }
        refs[name] = Entry(kind, address)
        return true
    }

    fun getRef(name: String): String = refs[name]?.address ?: ""

    fun deleteRef(name: String): Boolean = refs.remove(name) != null

    fun collectGarbage(): Int {
        val live =
            try {
                mark()
            } catch (e: Damaged) {
                return -1
            }
        val dead = objects.keys.filter { it !in live }
        val freed = dead.sumOf { objects.getValue(it).size }
        dead.forEach { objects.remove(it) }
        return freed
    }

    private fun mark(): Set<String> {
        val live = mutableSetOf<String>()
        val visited = mutableSetOf<Entry>()
        val pending = ArrayDeque(refs.values)
        while (pending.isNotEmpty()) {
            val entry = pending.removeLast()
            if (!visited.add(entry)) {
                continue
            }
            live += entry.address
            when (entry.kind) {
                "tree" -> pending.addAll(openTree(entry.address).values)
                "manifest" -> {
                    val listing = read(entry.address) ?: throw Damaged(entry.address)
                    lines(listing).forEach { pending.addLast(Entry("blob", it)) }
                }
            }
        }
        return live
    }
}
