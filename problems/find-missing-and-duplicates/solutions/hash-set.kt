class Solution {
    fun findMissingAndDuplicates(nums: IntArray): List<List<Int>> {
        val seen = HashSet<Int>()
        val repeated = HashSet<Int>()
        for (value in nums) {
            if (!seen.add(value)) {
                repeated.add(value)
            }
        }
        // Walking 1..n instead of the sets keeps both answers sorted without a sort.
        val values = 1..nums.size
        return listOf(values.filter { it !in seen }, values.filter { it in repeated })
    }
}
