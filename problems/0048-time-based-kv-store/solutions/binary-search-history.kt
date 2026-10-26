class TimeMap {
    private class History {
        val timestamps = ArrayList<Int>()
        val values = ArrayList<String>()
    }

    private val history = HashMap<String, History>()

    fun set(key: String, value: String, timestamp: Int) {
        val entries = history.getOrPut(key) { History() }
        entries.timestamps.add(timestamp)
        entries.values.add(value)
    }

    fun get(key: String, timestamp: Int): String {
        val entries = history[key] ?: return ""
        // binarySearch returns the index when found, otherwise -(insertion point) - 1.
        val found = entries.timestamps.binarySearch(timestamp)
        val count = if (found >= 0) found + 1 else -(found + 1)
        return if (count > 0) entries.values[count - 1] else ""
    }
}
