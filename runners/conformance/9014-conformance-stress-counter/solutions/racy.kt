class StressCounter {
    private var count = 0

    fun increment(): Int {
        val current = count
        count = current + 1
        return current + 1
    }
}
