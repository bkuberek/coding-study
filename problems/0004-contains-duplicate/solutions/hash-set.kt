class Solution {
    fun containsDuplicate(nums: IntArray): Boolean {
        val seen = HashSet<Int>()
        for (value in nums) {
            // add returns false when the value is already present.
            if (!seen.add(value)) {
                return true
            }
        }
        return false
    }
}
