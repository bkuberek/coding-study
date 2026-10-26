class NumArray(nums: IntArray) {
    private val nums = nums.copyOf()

    fun update(index: Int, value: Int) {
        nums[index] = value
    }

    fun sumRange(left: Int, right: Int): Long {
        var total = 0L
        for (i in left..right) {
            total += nums[i]
        }
        return total
    }
}
