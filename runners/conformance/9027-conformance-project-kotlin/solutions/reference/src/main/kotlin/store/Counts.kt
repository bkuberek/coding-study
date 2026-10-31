package store

/** Stock counts by name. */
internal class Counts {
    private val counts = mutableMapOf<String, Int>()

    fun add(name: String, count: Int): Int = (counts.getOrDefault(name, 0) + count).also { counts[name] = it }

    fun of(name: String): Int = counts.getOrDefault(name, 0)
}
