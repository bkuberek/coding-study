class BoundedBlockingQueue(private val capacity: Int) {
    private val items = java.util.ArrayDeque<Int>()

    fun put(value: Int) {
        while (items.size >= capacity) {
            Thread.sleep(0)
        }
        items.addLast(value)
    }

    fun take(): Int {
        while (items.isEmpty()) {
            Thread.sleep(0)
        }
        return items.pollFirst()
    }

    fun size(): Int = items.size
}
