import kotlin.math.abs

class Solution {
    fun minCostConnectPoints(points: Array<IntArray>): Int {
        val n = points.size
        // cheapest[i] is the cheapest cable from point i to the tree built so far.
        val cheapest = IntArray(n) { Int.MAX_VALUE }
        val inTree = BooleanArray(n)
        cheapest[0] = 0
        var total = 0
        repeat(n) {
            val point = (0 until n).filter { !inTree[it] }.minBy { cheapest[it] }
            inTree[point] = true
            total += cheapest[point]
            val (x, y) = points[point]
            for (other in 0 until n) {
                if (!inTree[other]) {
                    val cost = abs(x - points[other][0]) + abs(y - points[other][1])
                    if (cost < cheapest[other]) cheapest[other] = cost
                }
            }
        }
        return total
    }
}
