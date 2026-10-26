class Solution {
    fun twoSumSorted(numbers: IntArray, target: Int): IntArray {
        for (i in 0 until numbers.size - 1) {
            val j = numbers.binarySearch(target - numbers[i], fromIndex = i + 1)
            if (j >= 0) {
                return intArrayOf(i, j)
            }
        }
        return intArrayOf()
    }
}
