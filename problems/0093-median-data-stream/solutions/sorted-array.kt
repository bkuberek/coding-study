class MedianFinder {
    private val values = ArrayList<Int>() // every number so far, ascending

    fun addNum(num: Int) {
        // binarySearch returns -(insertion point) - 1 when num is absent.
        val index = values.binarySearch(num)
        values.add(if (index >= 0) index else -index - 1, num)
    }

    fun findMedian(): Double {
        val middle = values.size / 2
        return if (values.size % 2 == 1) {
            values[middle].toDouble()
        } else {
            (values[middle - 1] + values[middle]) / 2.0
        }
    }
}
