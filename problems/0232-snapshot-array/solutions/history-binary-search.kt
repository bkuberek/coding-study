class SnapshotArray(length: Int) {
    // history[i] holds {snapshot id, value} pairs with strictly increasing snapshot ids.
    private val history = Array(length) { mutableListOf<IntArray>() }
    private var snaps = 0

    fun set(index: Int, value: Int) {
        val entries = history[index]
        if (entries.isNotEmpty() && entries.last()[0] == snaps) {
            entries.last()[1] = value // overwrite within the same snapshot
        } else {
            entries.add(intArrayOf(snaps, value))
        }
    }

    fun snap(): Int = snaps++

    fun get(index: Int, snapId: Int): Int {
        val entries = history[index]
        // Upper bound: how many changes happened at or before snapId. (The library's
        // binarySearch reports a missing key as -(insertion point) - 1, which is clumsy here.)
        var low = 0
        var high = entries.size
        while (low < high) {
            val middle = (low + high) ushr 1
            if (entries[middle][0] <= snapId) {
                low = middle + 1
            } else {
                high = middle
            }
        }
        return if (low > 0) entries[low - 1][1] else 0
    }
}
