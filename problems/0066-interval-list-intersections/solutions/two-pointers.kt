class Solution {
    fun intervalIntersection(firstList: Array<IntArray>, secondList: Array<IntArray>): Array<IntArray> {
        val common = ArrayList<IntArray>()
        var i = 0
        var j = 0
        while (i < firstList.size && j < secondList.size) {
            val (firstStart, firstEnd) = firstList[i]
            val (secondStart, secondEnd) = secondList[j]
            val start = maxOf(firstStart, secondStart)
            val end = minOf(firstEnd, secondEnd)
            if (start <= end) {
                common.add(intArrayOf(start, end))
            }
            // The interval that ends first cannot meet anything later in the other list.
            if (firstEnd < secondEnd) i++ else j++
        }
        return common.toTypedArray()
    }
}
