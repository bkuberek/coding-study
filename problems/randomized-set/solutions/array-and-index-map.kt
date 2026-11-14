class RandomizedSet {
    private val values = ArrayList<Int>()
    private val indexOf = HashMap<Int, Int>()

    fun insert(value: Int): Boolean {
        if (value in indexOf) {
            return false
        }
        indexOf[value] = values.size
        values.add(value)
        return true
    }

    fun remove(value: Int): Boolean {
        val index = indexOf.remove(value) ?: return false
        val last = values.removeAt(values.lastIndex)
        if (index < values.size) {
            // Fill the gap with the former last value and record its new position.
            values[index] = last
            indexOf[last] = index
        }
        return true
    }

    fun getRandom(): Int = values.random()
}
