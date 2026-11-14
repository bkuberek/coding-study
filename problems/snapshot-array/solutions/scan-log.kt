class SnapshotArray(length: Int) {
    // Each entry is {index, value, snapshots taken before the write}.
    private val log = ArrayList<IntArray>()
    private var snaps = 0

    fun set(index: Int, value: Int) {
        log.add(intArrayOf(index, value, snaps))
    }

    fun snap(): Int = snaps++

    fun get(index: Int, snapId: Int): Int {
        // The newest write to index that happened before snapshot snapId was taken.
        for (i in log.indices.reversed()) {
            val (written, value, snapsBefore) = log[i]
            if (written == index && snapsBefore <= snapId) {
                return value
            }
        }
        return 0
    }
}
