class LRUCache(private val capacity: Int) {
    // accessOrder = true: every get or put moves the key to the end of the iteration order.
    private val entries = object : LinkedHashMap<Int, Int>(16, 0.75f, true) {
        override fun removeEldestEntry(eldest: MutableMap.MutableEntry<Int, Int>?): Boolean =
            size > capacity
    }

    fun get(key: Int): Int = entries[key] ?: -1

    fun put(key: Int, value: Int) {
        entries[key] = value
    }
}
