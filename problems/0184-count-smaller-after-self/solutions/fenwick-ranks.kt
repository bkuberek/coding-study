class Solution {
    fun countSmaller(nums: IntArray): IntArray {
        // Coordinate compression: the rank of a value is its position among the distinct values, plus 1.
        val distinct = nums.distinct().sorted().toIntArray()
        val size = distinct.size
        val tree = IntArray(size + 1) // how many seen values have each rank
        val counts = IntArray(nums.size)
        for (i in nums.indices.reversed()) {
            val rank = distinct.binarySearch(nums[i]) + 1
            // Seen values with a rank below this one, i.e. strictly smaller values to the right.
            var smaller = 0
            var j = rank - 1
            while (j > 0) {
                smaller += tree[j]
                j -= j and -j
            }
            counts[i] = smaller
            j = rank
            while (j <= size) {
                tree[j]++
                j += j and -j
            }
        }
        return counts
    }
}
