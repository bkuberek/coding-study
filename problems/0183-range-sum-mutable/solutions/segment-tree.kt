class NumArray(nums: IntArray) {
    private val size = nums.size

    // Leaves at size .. 2 * size - 1; node i holds the sum of its children 2i and 2i + 1.
    private val tree = LongArray(2 * size)

    init {
        for (i in nums.indices) tree[size + i] = nums[i].toLong()
        for (node in size - 1 downTo 1) tree[node] = tree[2 * node] + tree[2 * node + 1]
    }

    fun update(index: Int, value: Int) {
        var node = index + size
        tree[node] = value.toLong()
        while (node > 1) {
            node = node shr 1
            tree[node] = tree[2 * node] + tree[2 * node + 1]
        }
    }

    fun sumRange(left: Int, right: Int): Long {
        var total = 0L
        // Half-open [low, high) over the leaves, narrowed one level per round.
        var low = left + size
        var high = right + size + 1
        while (low < high) {
            if ((low and 1) == 1) total += tree[low++]
            if ((high and 1) == 1) total += tree[--high]
            low = low shr 1
            high = high shr 1
        }
        return total
    }
}
