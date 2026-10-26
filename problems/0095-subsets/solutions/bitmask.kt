class Solution {
    fun subsets(nums: IntArray): List<List<Int>> =
        // Bit i of mask says whether nums[i] belongs to the subset that mask encodes.
        (0 until (1 shl nums.size)).map { mask ->
            nums.filterIndexed { i, _ -> (mask shr i) and 1 == 1 }
        }
}
