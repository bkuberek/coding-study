class MinStack {
    // Each entry is a value and the minimum of this value and everything below it.
    private data class Entry(val value: Int, val minimum: Int)

    private val entries = ArrayDeque<Entry>()

    fun push(value: Int) {
        val minimum = entries.lastOrNull()?.let { minOf(value, it.minimum) } ?: value
        entries.addLast(Entry(value, minimum))
    }

    fun pop() {
        entries.removeLast()
    }

    fun top(): Int = entries.last().value

    fun getMin(): Int = entries.last().minimum
}
