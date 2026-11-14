class Solution {
    fun minInterval(intervals: Array<IntArray>, queries: IntArray): IntArray =
        IntArray(queries.size) { j ->
            intervals
                .filter { (left, right) -> queries[j] in left..right }
                .minOfOrNull { (left, right) -> right - left + 1 } ?: -1
        }
}
