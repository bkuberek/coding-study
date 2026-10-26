class Solution {
    fun permute(nums: IntArray): List<List<Int>> {
        val result = mutableListOf<List<Int>>()
        val ordering = ArrayList<Int>(nums.size)
        val used = BooleanArray(nums.size)

        fun fillNextSlot() {
            if (ordering.size == nums.size) {
                result.add(ordering.toList())
                return
            }
            for (i in nums.indices) {
                if (used[i]) continue
                used[i] = true
                ordering.add(nums[i])
                fillNextSlot()
                ordering.removeAt(ordering.size - 1)
                used[i] = false
            }
        }

        fillNextSlot()
        return result
    }
}
