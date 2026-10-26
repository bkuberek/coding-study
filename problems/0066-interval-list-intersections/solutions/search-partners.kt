class Solution {
    fun intervalIntersection(firstList: Array<IntArray>, secondList: Array<IntArray>): Array<IntArray> {
        val common = ArrayList<IntArray>()
        for ((firstStart, firstEnd) in firstList) {
            var partner = firstEndingAtOrAfter(secondList, firstStart)
            while (partner < secondList.size && secondList[partner][0] <= firstEnd) {
                val (secondStart, secondEnd) = secondList[partner]
                common.add(intArrayOf(maxOf(firstStart, secondStart), minOf(firstEnd, secondEnd)))
                partner++
            }
        }
        return common.toTypedArray()
    }

    private fun firstEndingAtOrAfter(intervals: Array<IntArray>, time: Int): Int {
        var low = 0
        var high = intervals.size
        while (low < high) {
            val middle = (low + high) ushr 1
            if (intervals[middle][1] >= time) high = middle else low = middle + 1
        }
        return low
    }
}
