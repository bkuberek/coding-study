class Solution {
    fun intervalIntersection(firstList: Array<IntArray>, secondList: Array<IntArray>): Array<IntArray> {
        // Both lists are sorted and separate, so pairs taken in this order yield sorted output.
        val common = ArrayList<IntArray>()
        for ((firstStart, firstEnd) in firstList) {
            for ((secondStart, secondEnd) in secondList) {
                val start = maxOf(firstStart, secondStart)
                val end = minOf(firstEnd, secondEnd)
                if (start <= end) {
                    common.add(intArrayOf(start, end))
                }
            }
        }
        return common.toTypedArray()
    }
}
