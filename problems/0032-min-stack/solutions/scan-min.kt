class MinStack {
    private val values = ArrayList<Int>()

    fun push(value: Int) {
        values.add(value)
    }

    fun pop() {
        values.removeAt(values.lastIndex)
    }

    fun top(): Int = values.last()

    // minOf() scans the whole list: O(n) per call.
    fun getMin(): Int = values.minOf { it }
}
