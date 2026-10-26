class TimeMap {
    private class Entry(val timestamp: Int, val value: String)

    private val history = HashMap<String, MutableList<Entry>>()

    fun set(key: String, value: String, timestamp: Int) {
        history.getOrPut(key) { mutableListOf() }.add(Entry(timestamp, value))
    }

    fun get(key: String, timestamp: Int): String =
        history[key]?.lastOrNull { it.timestamp <= timestamp }?.value ?: ""
}
