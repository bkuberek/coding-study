class LevelStore {
    private val values = HashMap<String, String>()

    fun put(key: String, value: String) {
        values[key] = value
    }

    fun get(key: String): String = values[key] ?: ""

    fun remove(key: String): Boolean = values.remove(key) != null

    fun size(): Int = values.size

    fun keysWithPrefix(prefix: String): Array<String> =
        values.keys.filter { it.startsWith(prefix) }.sorted().toTypedArray()
}
