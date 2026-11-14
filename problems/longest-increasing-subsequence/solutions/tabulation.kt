class Solution {
    fun lengthOfLIS(nums: IntArray): Int {
        // ending[i] is the length of the longest increasing subsequence that ends at index i.
        val ending = IntArray(nums.size) { 1 }
        for (i in 1 until nums.size) {
            for (j in 0 until i) {
                if (nums[j] < nums[i] && ending[j] + 1 > ending[i]) {
                    ending[i] = ending[j] + 1
                }
            }
        }
        return ending.max()
    }
}
