import java.math.BigDecimal

class Solution {
    fun totalExposure(edges: Array<Array<String>>, contractors: Array<String>, exposures: Array<BigDecimal>, root: String): BigDecimal {
        val children = edges.groupBy({ it[0] }, { it[1] })
        val own = contractors.zip(exposures).toMap()
        val onPath = hashSetOf(root) // meeting one again closes a cycle
        val finished = hashSetOf<String>() // fully explored contractors, already counted
        var total = own[root] ?: BigDecimal.ZERO
        val stack = ArrayDeque<Pair<String, Iterator<String>>>()
        stack.addLast(root to (children[root] ?: emptyList()).iterator())
        while (stack.isNotEmpty()) {
            val (node, pending) = stack.last()
            if (!pending.hasNext()) {
                stack.removeLast()
                onPath.remove(node)
                finished.add(node)
                continue
            }
            val child = pending.next()
            if (child in onPath) {
                return BigDecimal.ONE.negate()
            }
            if (child !in finished) {
                onPath.add(child)
                total += own[child] ?: BigDecimal.ZERO
                stack.addLast(child to (children[child] ?: emptyList()).iterator())
            }
        }
        return total
    }
}
