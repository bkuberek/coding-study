class MinStack {
    private val values = ArrayDeque<Int>()

    // The minimums in the order they took effect; the last one is the current minimum.
    private val minimums = ArrayDeque<Int>()

    fun push(value: Int) {
        values.addLast(value)
        // <= keeps one copy per equal minimum, so popping one copy keeps the others.
        if (minimums.isEmpty() || value <= minimums.last()) {
            minimums.addLast(value)
        }
    }

    fun pop() {
        if (values.removeLast() == minimums.last()) {
            minimums.removeLast()
        }
    }

    fun top(): Int = values.last()

    fun getMin(): Int = minimums.last()
}
