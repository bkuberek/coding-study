class Counter {
    private var count = 0

    fun increment(): Int {
        count++
        return count
    }

    fun fail(): Int = error("counter failure")
}
