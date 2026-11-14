class KthLargestTracker(private val k: Int, nums: IntArray) {
    private val values = ArrayList<Int>(nums.sorted()) // every number so far, ascending

    fun add(value: Int): Int {
        // binarySearch returns -(insertion point) - 1 when the value is absent.
        val index = values.binarySearch(value)
        values.add(if (index >= 0) index else -index - 1, value)
        // The kth largest is the kth entry from the end.
        return values[values.size - k]
    }
}
