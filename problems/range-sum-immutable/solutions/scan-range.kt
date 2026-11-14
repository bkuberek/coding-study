class NumArray(private val nums: IntArray) {
    fun sumRange(left: Int, right: Int): Long {
        var total = 0L
        for (i in left..right) {
            total += nums[i]
        }
        return total
    }
}
