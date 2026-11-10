import kotlin.math.abs

class Solution {
    fun findMissingAndDuplicates(nums: IntArray): List<List<Int>> {
        val n = nums.size
        for (i in 0 until n) {
            // Swap nums[i] to its home index nums[i] - 1 until the home already holds that
            // value. Comparing with the home, not with i, is what stops the loop on a repeat.
            while (nums[nums[i] - 1] != nums[i]) {
                val home = nums[i] - 1
                val displaced = nums[home]
                nums[home] = nums[i]
                nums[i] = displaced
            }
        }

        // Every value that occurs now sits at its home. A slot that holds another value is
        // either the home of a missing value or a spare copy of a value that is home
        // elsewhere. A negative sign on a home marks that its value has a spare copy.
        val missing = mutableListOf<Int>()
        for (i in 0 until n) {
            if (abs(nums[i]) == i + 1) {
                continue
            }
            missing.add(i + 1)
            val spare = nums[i]
            nums[spare - 1] = -spare
        }

        // The marks are read in index order, so the duplicates come out sorted too.
        val duplicated = (1..n).filter { nums[it - 1] < 0 }
        return listOf(missing, duplicated)
    }
}
