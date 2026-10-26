class Solution {
    fun twoSumSorted(numbers: IntArray, target: Int): IntArray {
        for (i in numbers.indices) {
            for (j in i + 1 until numbers.size) {
                if (numbers[i] + numbers[j] == target) {
                    return intArrayOf(i, j)
                }
            }
        }
        return intArrayOf()
    }
}
