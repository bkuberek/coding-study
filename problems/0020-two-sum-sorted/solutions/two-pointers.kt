class Solution {
    fun twoSumSorted(numbers: IntArray, target: Int): IntArray {
        var left = 0
        var right = numbers.size - 1
        while (left < right) {
            val total = numbers[left] + numbers[right]
            when {
                total == target -> return intArrayOf(left, right)
                total < target -> left++
                else -> right--
            }
        }
        return intArrayOf()
    }
}
