class Solution {
    fun subsetsWithDup(nums: IntArray): List<List<Int>> {
        val ordered = nums.sorted()
        // Taking values in sorted order gives every multiset one canonical list; lists compare
        // by content, so a set keeps each one once.
        val distinct = LinkedHashSet<List<Int>>()
        for (mask in 0 until (1 shl ordered.size)) {
            distinct.add(ordered.filterIndexed { i, _ -> (mask shr i) and 1 == 1 })
        }
        return distinct.toList()
    }
}
