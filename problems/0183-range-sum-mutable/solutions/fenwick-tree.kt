class NumArray(nums: IntArray) {
    private val values = nums.copyOf()

    // tree[i] (1-based) holds the sum of the lowBit(i) values ending at position i - 1.
    private val tree = LongArray(nums.size + 1)

    init {
        for (i in 1..nums.size) {
            tree[i] += nums[i - 1].toLong()
            val parent = i + lowBit(i)
            if (parent <= nums.size) tree[parent] += tree[i]
        }
    }

    fun update(index: Int, value: Int) {
        val delta = value.toLong() - values[index]
        values[index] = value
        var i = index + 1
        while (i < tree.size) {
            tree[i] += delta
            i += lowBit(i)
        }
    }

    fun sumRange(left: Int, right: Int): Long = prefix(right + 1) - prefix(left)

    /** Sum of the first count values. */
    private fun prefix(count: Int): Long {
        var total = 0L
        var i = count
        while (i > 0) {
            total += tree[i]
            i -= lowBit(i)
        }
        return total
    }

    private fun lowBit(i: Int): Int = i and -i
}
