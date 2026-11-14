class Solution {
    fun permute(nums: IntArray): List<List<Int>> {
        val values = nums.copyOf()
        val result = mutableListOf<List<Int>>()

        fun swap(i: Int, j: Int) {
            val held = values[i]
            values[i] = values[j]
            values[j] = held
        }

        // values[0 until slot] is the fixed prefix; values[slot..] are the candidates still free.
        fun fixSlot(slot: Int) {
            if (slot == values.size) {
                result.add(values.toList())
                return
            }
            for (candidate in slot until values.size) {
                swap(slot, candidate)
                fixSlot(slot + 1)
                swap(slot, candidate)
            }
        }

        fixSlot(0)
        return result
    }
}
