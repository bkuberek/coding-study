class Solution {
    fun findMissingAndDuplicates(nums: IntArray): List<List<Int>> {
        nums.sort()
        val missing = mutableListOf<Int>()
        val duplicated = mutableListOf<Int>()
        var expected = 1 // the smallest value not accounted for yet
        var previous = 0
        for (value in nums) {
            if (value == previous) {
                // A third copy must not list the value again.
                if (duplicated.lastOrNull() != value) {
                    duplicated.add(value)
                }
                continue
            }
            while (expected < value) {
                missing.add(expected)
                expected++
            }
            expected = value + 1
            previous = value
        }
        while (expected <= nums.size) {
            missing.add(expected)
            expected++
        }
        return listOf(missing, duplicated)
    }
}
