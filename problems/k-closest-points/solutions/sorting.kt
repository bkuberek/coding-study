class Solution {
    fun kClosest(points: Array<IntArray>, k: Int): Array<IntArray> =
        // Squared distances order points exactly like distances, without square roots.
        points.sortedBy { (x, y) -> x * x + y * y }.take(k).toTypedArray()
}
