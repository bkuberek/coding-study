class Solution {
    fun subsets(nums: IntArray): List<List<Int>> {
        val result = mutableListOf<List<Int>>()
        val chosen = ArrayList<Int>()

        fun explore(index: Int) {
            if (index == nums.size) {
                result.add(chosen.toList())
                return
            }
            chosen.add(nums[index])
            explore(index + 1)
            chosen.removeAt(chosen.size - 1)
            explore(index + 1)
        }

        explore(0)
        return result
    }
}
