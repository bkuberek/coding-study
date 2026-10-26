class NumArray(nums: IntArray) {
    // prefix[i] is the sum of nums[0 until i]; Long because a sum can pass 2^31.
    private val prefix = LongArray(nums.size + 1)

    init {
        for (i in nums.indices) {
            prefix[i + 1] = prefix[i] + nums[i]
        }
    }

    fun sumRange(left: Int, right: Int): Long = prefix[right + 1] - prefix[left]
}
