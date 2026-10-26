class RandomizedSet {
    private val values = ArrayList<Int>()

    fun insert(value: Int): Boolean {
        // `in` (contains) is a linear scan: O(n) per call.
        if (value in values) {
            return false
        }
        values.add(value)
        return true
    }

    fun remove(value: Int): Boolean {
        val index = values.indexOf(value)
        if (index == -1) {
            return false
        }
        // Order does not matter: move the last value into the gap instead of shifting.
        val last = values.removeAt(values.lastIndex)
        if (index < values.size) {
            values[index] = last
        }
        return true
    }

    fun getRandom(): Int = values.random()
}
