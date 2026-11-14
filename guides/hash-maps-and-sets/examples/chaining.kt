import java.util.zip.CRC32

// A hash map with separate chaining that doubles its buckets when the load factor passes 0.75.
//
// It hashes with CRC-32, the checksum zlib computes, so every run, in every language, fills the
// same buckets.

const val MAX_LOAD = 0.75

class Entry(val key: String, var value: Int)

class ChainedMap(buckets: Int = 4) {
    var buckets: List<MutableList<Entry>> = List(buckets) { mutableListOf() }
        private set
    var size = 0
        private set
    var moved = 0L // entries copied by every resize so far
        private set

    private fun bucketOf(key: String): MutableList<Entry> {
        val crc = CRC32().apply { update(key.toByteArray()) }
        return buckets[(crc.value % buckets.size).toInt()]
    }

    fun put(key: String, value: Int) {
        val chain = bucketOf(key)
        // A collision is fine: compare the keys themselves.
        val stored = chain.find { it.key == key }
        if (stored != null) {
            stored.value = value
            return
        }
        chain.add(Entry(key, value))
        size += 1
        if (size.toDouble() / buckets.size > MAX_LOAD) resize(2 * buckets.size)
    }

    fun get(key: String): Int? = bucketOf(key).find { it.key == key }?.value

    private fun resize(count: Int) {
        val entries = buckets.flatten()
        buckets = List(count) { mutableListOf() }
        for (entry in entries) bucketOf(entry.key).add(entry)
        moved += entries.size
    }
}

fun main() {
    val ages = ChainedMap()
    listOf("ada", "bo", "cy", "di").forEachIndexed { index, name ->
        ages.put(name, 30 + index)
        println("put $name: ${ages.size} entries in ${ages.buckets.size} buckets")
    }
    println("get('cy') = ${ages.get("cy")} | get('zed') = ${ages.get("zed")}")

    for (count in listOf(1_000, 100_000)) {
        val table = ChainedMap()
        for (number in 0 until count) table.put("key$number", number)
        val longest = table.buckets.maxOf { it.size }
        println(
            "%7d puts: %6d buckets, %.2f moves per put, longest chain %d"
                .format(count, table.buckets.size, table.moved.toDouble() / count, longest),
        )
    }
}
