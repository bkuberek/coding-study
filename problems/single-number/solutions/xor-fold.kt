class Solution {
    // Kotlin spells XOR as the infix function xor; pairs cancel because a xor a == 0.
    fun singleNumber(nums: IntArray): Int = nums.fold(0) { result, value -> result xor value }
}
