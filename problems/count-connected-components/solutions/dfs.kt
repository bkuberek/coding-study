class Solution {
    fun countComponents(n: Int, edges: Array<IntArray>): Int {
        val neighbors = List(n) { mutableListOf<Int>() }
        for ((a, b) in edges) {
            neighbors[a].add(b)
            neighbors[b].add(a)
        }
        val seen = BooleanArray(n)
        var components = 0
        val stack = ArrayDeque<Int>() // an explicit stack avoids deep recursion on long paths
        for (start in 0 until n) {
            if (seen[start]) continue
            components++
            seen[start] = true
            stack.addLast(start)
            while (stack.isNotEmpty()) {
                for (neighbor in neighbors[stack.removeLast()]) {
                    if (!seen[neighbor]) {
                        seen[neighbor] = true
                        stack.addLast(neighbor)
                    }
                }
            }
        }
        return components
    }
}
