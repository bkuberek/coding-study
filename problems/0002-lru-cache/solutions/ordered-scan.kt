class LRUCache(private val capacity: Int) {
    private class Entry(val key: Int, val value: Int)

    // Ordered from least to most recently used.
    private val entries = mutableListOf<Entry>()

    fun get(key: Int): Int {
        val index = entries.indexOfFirst { it.key == key }
        if (index < 0) return -1
        val entry = entries.removeAt(index)
        entries.add(entry)
        return entry.value
    }

    fun put(key: Int, value: Int) {
        val index = entries.indexOfFirst { it.key == key }
        if (index >= 0) {
            entries.removeAt(index)
        } else if (entries.size == capacity) {
            entries.removeAt(0)
        }
        entries.add(Entry(key, value))
    }
}
