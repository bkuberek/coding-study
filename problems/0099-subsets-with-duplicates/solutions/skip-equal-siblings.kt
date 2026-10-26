class Solution {
    fun subsetsWithDup(nums: IntArray): List<List<Int>> {
        val ordered = nums.sorted()
        val result = mutableListOf<List<Int>>()
        val chosen = ArrayList<Int>()

        fun extend(start: Int) {
            // Every node of this recursion is a distinct subset.
            result.add(chosen.toList())
            for (i in start until ordered.size) {
                // A second copy at the same level would rebuild the first copy's subtree.
                if (i > start && ordered[i] == ordered[i - 1]) continue
                chosen.add(ordered[i])
                extend(i + 1)
                chosen.removeAt(chosen.size - 1)
            }
        }

        extend(0)
        return result
    }
}
